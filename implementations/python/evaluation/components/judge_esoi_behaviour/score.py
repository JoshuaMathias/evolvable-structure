"""Score one judge call: the verdict must equal the label of the reply it graded. ``aggregate`` reports agreement per side
(good replies passed, bad replies failed), the two error kinds, and how many labels are a person's own."""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
BEHAVIOR_CASES = HERE.parent / "behave_by_esoi" / "cases.csv"
COLUMNS = ["id", "case_id", "side", "area", "expected", "human_verdict", "heldout"]
SIDES = (("good", "pass"), ("bad", "fail"))


def behavior_cases():
    with BEHAVIOR_CASES.open(newline="", encoding="utf-8") as fh:
        return {row["id"]: row for row in csv.DictReader(fh)}


def label(case):
    """The answer key for a judge case: a person's verdict when there is one, else the case author's label."""
    return (case.get("human_verdict") or "").strip().lower() or case["expected"]


def join(case):
    """The judge case joined to its behaviour case and the recorded reply for its side."""
    source = behavior_cases()[case["case_id"]]
    reply = source["good_reference" if case["side"] == "good" else "bad_reference"]
    return dict(case, behavior_case=source, reply=reply)


def score_case(fn, case):
    out = fn(join(case))
    verdict = str(out.get("verdict", "")).strip().lower()
    return dict(ok=verdict == label(case), got=case["side"], human=bool((case.get("human_verdict") or "").strip()),
                note=f"{verdict} (label {label(case)}): {out.get('reason', '')}"[:200])


def aggregate(rows):
    sides = {}
    for r in rows:
        passed, total = sides.get(r.get("got"), (0, 0))
        sides[r.get("got")] = (passed + bool(r.get("ok")), total + 1)
    good, bad = sides.get("good", (0, 0)), sides.get("bad", (0, 0))
    human = sum(bool(r.get("human")) for r in rows)
    return (f"agreement {good[0] + bad[0]}/{good[1] + bad[1]}; good replies passed {good[0]}/{good[1]} "
            f"(false fails {good[1] - good[0]}), bad replies failed {bad[0]}/{bad[1]} (false passes {bad[1] - bad[0]}); "
            f"labels from a person {human}/{len(rows)}")


def rows_for(source_cases, human=None):
    """The judge case rows (two per behaviour case) for these behaviour cases, keeping any human verdicts already given."""
    human = human or {}
    out = []
    for c in source_cases:
        for side, expected in SIDES:
            key = f"{c['id']}-{side}"
            out.append({"id": key, "case_id": c["id"], "side": side, "area": c.get("area", ""), "expected": expected,
                        "human_verdict": human.get(key, ""), "heldout": "yes" if c.get("heldout") else ""})
    return out


def write_cases(path=HERE / "cases.csv"):
    """Regenerate ``cases.csv`` from the behaviour cases, keeping the human verdicts already in it. Run it when
    ``behave_by_esoi/cases.csv`` changes; a test fails while the two disagree."""
    path = Path(path)
    human = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            human = {r["id"]: r["human_verdict"] for r in csv.DictReader(fh)}
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_for(behavior_cases().values(), human))
