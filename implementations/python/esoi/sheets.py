"""Two-way sync between tracker CSVs and a Google Sheet (optional: ``pip install "esoi[sheets]"``).

    esoi sheet-sync sync [--dry-run]   # merge both sides by each tab's key column, write the result to both
    esoi sheet-sync push [--dry-run]   # the CSV overwrites the sheet
    esoi sheet-sync pull [--dry-run]   # the sheet overwrites the CSV
    esoi sheet-sync check              # read the sheet back and compare ids with the CSVs

Nothing private is in this module. The sheet id and the service-account credentials file come from the
environment (``ESOI_SHEET_ID``, ``ESOI_SHEETS_CREDENTIALS``) or the ``[sheets]`` table of the configuration, and
the tabs are a map of tab title to CSV path:

    [sheets]
    sheet_id_env = "ESOI_SHEET_ID"                  # the variable that holds the id (the default)
    credentials_env = "ESOI_SHEETS_CREDENTIALS"     # the variable that holds the key file path (the default)
    state_file = ".esoi_sync_state.json"            # last-synced row hashes (gitignored)
    [sheets.tabs]
    Problems = { csv = "esoi/tracker/problems.csv", key = "problem_id", prefix = "PROB-" }

Without ``[sheets.tabs]`` the five tracker tabs are synced. The service account must be shared on the sheet.

Merge rules for ``sync`` (per row, keyed by the tab's key column, against the hash stored at the last sync): a
row changed on one side only takes that side; a new row on either side is kept; a row changed on both sides
takes the sheet version and prints the CSV version as a conflict; a row deleted on one side and unchanged on the
other is deleted. A sheet row with a blank key gets the next free id for its tab. Values are written RAW so text
never turns into a number or a date. The merge is plain functions (``merge``), so it is tested without a network;
the API calls are behind ``SheetsApi``.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .config import Config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TRACKER_KEYS = {"problems": ("Problems", "problem_id", "PROB-"), "solutions": ("Solutions", "solution_id", "SOL-"),
                "implementations": ("Implementations", "implementation_id", "IMPL-"),
                "ideals": ("Ideals", "ideal_id", "IDEAL-"), "metrics": ("Metrics", "metric_id", "METRIC-")}
Row = Dict[str, str]


def row_hash(header: List[str], row: Row) -> str:
    return hashlib.sha256(json.dumps([row.get(h, "") for h in header], ensure_ascii=False).encode()).hexdigest()[:16]


def read_table(path: Path) -> Tuple[List[str], List[Row]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return [], []
    header = rows[0]
    out = []
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        r = r + [""] * (len(header) - len(r))
        out.append(dict(zip(header, r)))
    return header, out


def write_table(path: Path, header: List[str], rows: List[Row]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        for r in rows:
            writer.writerow([r.get(h, "") for h in header])


def next_id(prefix: str, existing: List[str]) -> str:
    nums = [int(m.group(1)) for i in existing if (m := re.match(re.escape(prefix) + r"(\d+)$", i))]
    return f"{prefix}{(max(nums) + 1 if nums else 1):03d}"


def merge(csv_header: List[str], csv_rows: List[Row], sheet_header: List[str], sheet_rows: List[Row],
          base: Dict[str, str], prefix: str, key: str) -> Tuple[List[str], List[Row], List[str]]:
    """Return (header, merged rows, log lines). ``base`` is {key: hash} from the last sync."""
    header = list(csv_header) or list(sheet_header)
    header += [h for h in sheet_header if h and h not in header]
    log: List[str] = []
    all_ids = [r[key] for r in csv_rows] + [r.get(key, "") for r in sheet_rows]
    for r in sheet_rows:   # a blank id in the sheet -> assign the next free one
        if not r.get(key, "").strip():
            r[key] = next_id(prefix, all_ids)
            all_ids.append(r[key])
            log.append(f"  new id {r[key]} assigned to a sheet row")
    by_csv = {r[key]: r for r in csv_rows}
    by_sheet = {r[key]: r for r in sheet_rows}
    order = [r[key] for r in csv_rows] + [r[key] for r in sheet_rows if r[key] not in by_csv]
    out: List[Row] = []
    for i in order:
        cr, sr, b = by_csv.get(i), by_sheet.get(i), base.get(i)
        hc = row_hash(header, cr) if cr else None
        hs = row_hash(header, sr) if sr else None
        if cr and sr:
            if hc == hs or hc == b:
                out.append(sr)
                if hc != hs:
                    log.append(f"  {i}: changed in sheet")
            elif hs == b:
                out.append(cr)
                log.append(f"  {i}: changed in CSV")
            else:
                out.append(sr)
                log.append(f"  CONFLICT {i}: changed on both sides, sheet wins. CSV version was:\n"
                           + json.dumps({h: cr.get(h, "") for h in header}, ensure_ascii=False, indent=1))
        elif cr:
            if b is None:
                out.append(cr)
                log.append(f"  {i}: new in CSV")
            elif hc == b:
                log.append(f"  {i}: deleted in sheet, deleting from CSV")
            else:
                out.append(cr)
                log.append(f"  {i}: deleted in sheet but changed in CSV, kept")
        else:
            if b is None:
                out.append(sr)
                log.append(f"  {i}: new in sheet")
            elif hs == b:
                log.append(f"  {i}: deleted in CSV, deleting from sheet")
            else:
                out.append(sr)
                log.append(f"  {i}: deleted in CSV but changed in sheet, kept")
    return header, out, log


class SheetsApi:
    """The few Google Sheets calls the sync needs; replaced by a fake in tests."""

    def __init__(self, sheet_id: str, credentials_file: str):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        self.sheet_id = sheet_id
        self.api = build("sheets", "v4", credentials=creds, cache_discovery=False).spreadsheets()

    def titles(self) -> Dict[str, int]:
        meta = self.api.get(spreadsheetId=self.sheet_id, fields="sheets(properties)").execute()
        return {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}

    def ensure_tabs(self, wanted: List[str]) -> None:
        have = self.titles()
        spare = [t for t in have if t not in wanted and re.fullmatch(r"Sheet\d+", t)]
        requests = []
        for title in wanted:
            if title in have:
                continue
            if spare:
                old = spare.pop(0)
                requests.append({"updateSheetProperties": {"properties": {"sheetId": have[old], "title": title}, "fields": "title"}})
            else:
                requests.append({"addSheet": {"properties": {"title": title}}})
        if requests:
            self.api.batchUpdate(spreadsheetId=self.sheet_id, body={"requests": requests}).execute()

    def read(self, title: str) -> Tuple[List[str], List[Row]]:
        res = self.api.values().get(spreadsheetId=self.sheet_id, range=f"'{title}'!A1:ZZ",
                                    valueRenderOption="FORMATTED_VALUE").execute()
        values = res.get("values", [])
        if not values:
            return [], []
        header = [h.strip() for h in values[0]]
        rows = []
        for r in values[1:]:
            if not any(str(c).strip() for c in r):
                continue
            r = [str(c) for c in r] + [""] * (len(header) - len(r))
            rows.append(dict(zip(header, r)))
        return header, rows

    def write(self, title: str, header: List[str], rows: List[Row]) -> None:
        values = [header] + [[r.get(h, "") for h in header] for r in rows]
        self.api.values().clear(spreadsheetId=self.sheet_id, range=f"'{title}'").execute()
        self.api.values().update(spreadsheetId=self.sheet_id, range=f"'{title}'!A1", valueInputOption="RAW",
                                 body={"values": values}).execute()

    def format(self, titles: List[str], headers: Dict[str, List[str]]) -> None:
        """Frozen bold header row, wrapped text and a filter on each synced tab."""
        ids = self.titles()
        requests = []
        for title in titles:
            sid = ids[title]
            requests += [
                {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}},
                                           "fields": "gridProperties.frozenRowCount"}},
                {"repeatCell": {"range": {"sheetId": sid}, "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}},
                                "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}},
                {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
                                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                                "fields": "userEnteredFormat.textFormat"}},
                {"setBasicFilter": {"filter": {"range": {"sheetId": sid, "startRowIndex": 0, "startColumnIndex": 0,
                                                         "endColumnIndex": len(headers.get(title, []))}}}}]
        if requests:
            self.api.batchUpdate(spreadsheetId=self.sheet_id, body={"requests": requests}).execute()


def tabs_from(config: Config) -> Dict[str, Tuple[Path, str, str]]:
    """{tab title: (csv path, key column, id prefix)} from ``[sheets.tabs]`` or the five tracker tabs."""
    table = config.sheets.get("tabs")
    if table:
        return {title: (config.root / spec["csv"], spec["key"], spec.get("prefix", "ID-")) for title, spec in table.items()}
    return {title: (config.tracker_dir / f"{tab}.csv", key, prefix) for tab, (title, key, prefix) in TRACKER_KEYS.items()}


def settings(config: Config) -> Tuple[str, str]:
    """(sheet id, credentials file) from the configured environment variables, else the config table."""
    table = config.sheets
    sheet_id = os.environ.get(table.get("sheet_id_env", "ESOI_SHEET_ID")) or table.get("sheet_id", "")
    credentials = os.environ.get(table.get("credentials_env", "ESOI_SHEETS_CREDENTIALS")) or table.get("credentials", "")
    if not sheet_id or not credentials:
        raise SystemExit("sheet-sync needs a sheet id and a credentials file: set "
                         f"{table.get('sheet_id_env', 'ESOI_SHEET_ID')} and {table.get('credentials_env', 'ESOI_SHEETS_CREDENTIALS')}")
    return sheet_id, str(Path(credentials).expanduser())


def run_sync(config: Config, api, mode: str, dry_run: bool = False, say: Callable[[str], None] = print) -> int:
    tabs = tabs_from(config)
    state_path = config.root / config.sheets.get("state_file", ".esoi_sync_state.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    if not dry_run:
        api.ensure_tabs(list(tabs))
    headers: Dict[str, List[str]] = {}
    for title, (path, key, prefix) in tabs.items():
        if not path.exists():   # never read a missing file as "everything deleted"
            say(f"[{title}] SKIPPED: {path.name} not found")
            continue
        csv_header, csv_rows = read_table(path)
        try:
            sheet_header, sheet_rows = api.read(title)
        except Exception:
            if not dry_run:
                raise
            sheet_header, sheet_rows = [], []   # a tab not created yet in a dry run
        if mode == "push":
            header, rows, log = csv_header, csv_rows, ["  CSV overwrites sheet"]
        elif mode == "pull":
            header, rows, log = sheet_header, sheet_rows, ["  sheet overwrites CSV"]
        else:
            header, rows, log = merge(csv_header, csv_rows, sheet_header, sheet_rows,
                                      state.get(title, {}).get("rows", {}), prefix, key)
        say(f"[{title}] csv={len(csv_rows)} sheet={len(sheet_rows)} -> {len(rows)} rows")
        for line in log:
            say(line)
        keys = [r[key] for r in rows]
        dup = sorted({k for k in keys if keys.count(k) > 1})
        if dup:
            raise SystemExit(f"duplicate ids in {title}: {dup}; fix them before syncing")
        headers[title] = header
        if dry_run or not header:
            continue
        write_table(path, header, rows)
        api.write(title, header, rows)
        state[title] = {"header": header, "rows": {r[key]: row_hash(header, r) for r in rows}}
    if dry_run:
        say("dry run: nothing written")
        return 0
    api.format([t for t, h in headers.items() if h], headers)
    state_path.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    say("done")
    return 0 if run_check(config, api, say) else 1


def run_check(config: Config, api, say: Callable[[str], None] = print) -> bool:
    ok = True
    for title, (path, key, _) in tabs_from(config).items():
        if not path.exists():
            continue
        _, csv_rows = read_table(path)
        _, sheet_rows = api.read(title)
        same = [r[key] for r in csv_rows] == [r.get(key) for r in sheet_rows]
        say(f"check [{title}]: csv={len(csv_rows)} sheet={len(sheet_rows)} ids_match={same}")
        ok &= same
    say("check: " + ("OK" if ok else "MISMATCH"))
    return ok


def run_cli(config: Config, mode: str, dry_run: bool, say: Callable[[str], None] = print) -> int:
    sheet_id, credentials = settings(config)
    try:
        api = SheetsApi(sheet_id, credentials)
    except ImportError:
        raise SystemExit('Google Sheets support is optional: pip install "esoi[sheets]"')
    if mode == "check":
        return 0 if run_check(config, api, say) else 1
    return run_sync(config, api, mode, dry_run, say)
