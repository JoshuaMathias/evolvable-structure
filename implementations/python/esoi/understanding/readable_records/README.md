# Readable Records

**Purpose:** Give every intent folder a page, made from its records, that says at a glance what the intent is and how its parts fit.

Breadcrumb: [Top](../../../../../esoi/README.md) > [How People and Agents Come to Apply ESOI](../README.md) > Readable Records

Part of [How People and Agents Come to Apply ESOI](../README.md)

## Readable Records (`readable-records`)

- Out of scope: Holding records; carrying a reviewer's edits back.
- Delegates to: intent-registry, review-tracker
- Entry call: `esoi.run("readable-records", '.')`
- Selected implementation: At a glance, full record below (`at_a_glance`)
- Metric: README glanceability, README fidelity
- Implemented by: [`implementations/python/esoi/structure/structure_check/check.py`](../../structure/structure_check/check.py), [`implementations/python/esoi/structure/structure_check/coherence.py`](../../structure/structure_check/coherence.py), [`implementations/python/esoi/structure/structure_check/coherence_code_evidence.py`](../../structure/structure_check/coherence_code_evidence.py), [`implementations/python/esoi/structure/structure_check/coherence_paragraph.py`](../../structure/structure_check/coherence_paragraph.py), [`implementations/python/esoi/structure/structure_check/coherence_records.py`](../../structure/structure_check/coherence_records.py), [`implementations/python/esoi/structure/structure_check/ratchet.py`](../../structure/structure_check/ratchet.py), [`implementations/python/esoi/structure/structure_check/rules/entry_rules.py`](../../structure/structure_check/rules/entry_rules.py), [`implementations/python/esoi/structure/structure_check/rules/generated.py`](../../structure/structure_check/rules/generated.py) and 43 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Record tables only | `readable-records:full_page` | A page is written into every intent folder from its records: what the intent is, how its solutions fit together in one paragraph, then its problems, ideals, solutions, implementations and metrics by id, in file order. The check reports a page that differs from what the records generate. | [`implementations/python/esoi/understanding/readable_records/interface.py`](interface.py) |  |
| At a glance, full record below | `readable-records:at_a_glance` | The page opens with the name, vision statement and opportunities, the paragraph on how the solutions fit, the solution diagram inline, a table of each solution's one-line entry call and selected implementation, problems and ideals in a line each, metrics with their current leader and links to the sub-intents, the parent intent and the repository's top README. A divider follows, and below it the full record tables. | [`implementations/python/esoi/understanding/readable_records/interface.py`](interface.py) | selected |
| Compact page of links | `readable-records:links_page` | The page holds the name, the vision statement and links: to each sub-intent, the parent intent, the repository's top README and each record file with its row count. | [`implementations/python/esoi/understanding/readable_records/interface.py`](interface.py) |  |
| README written by hand | `readable-records:hand-written-readme` | A person writes a summary of the intent beside the records. | no code yet |  |

## Metrics

- README fidelity (`metric-readme-fidelity`): leader `live_readme`, 10 of 10 cases
- README glanceability (`metric-readme-glanceability`): leader `at_a_glance`, 2 of 4 cases

## Problems

- Records unreadable at a glance (`prob-records-unreadable-at-a-glance`): An intent's folder of CSV files states it completely, but a person clicking into it cannot tell at a glance what the intent is for, how its solutions fit or where to go next: that takes opening several files and following ids between them.

## Ideals

- Glanceable intent (`ideal-glanceable-intent`): Anyone clicking into an intent folder sees on the first screen what the intent is, how its solutions fit together and where to go next.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [How People and Agents Come to Apply ESOI](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
