"""What the review-tracker arms report about one tab of the tracker they just wrote: the cell asked for, the tab's header and its row count."""
import csv


def tab_summary(cfg, args):
    rows = list(csv.DictReader((cfg.tracker_dir / f"{args.get('tab', 'solutions')}.csv").open()))
    header = list(rows[0].keys()) if rows else []
    hit = next((r for r in rows if r[header[0]] == args.get("key")), {}) if rows else {}
    return {"value": hit.get(args.get("column", ""), ""), "header": header, "rows": len(rows)}
