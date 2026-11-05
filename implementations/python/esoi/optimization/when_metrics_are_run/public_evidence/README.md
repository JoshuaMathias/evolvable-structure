# Grade Public Evidence

**Purpose:** Grade what others have measured about a candidate, so a measurement that costs money is made only when outside evidence cannot settle the question.

Breadcrumb: [Top](../../../../../../esoi/README.md) > [Implementations Chosen on Evidence](../../README.md) > [When Metrics Are Run](../README.md) > Grade Public Evidence

Part of [When Metrics Are Run](../README.md)

## Grade Public Evidence (`public-evidence`)

- Out of scope: Searching the literature for more evidence, merging different measures or comparators, converting units outside the table, and replacing the repository's own results.
- Delegates to: leaderboard
- Entry call: `esoi.run("public-evidence", {'evidence': []})`
- Selected implementation: Letter grades by weighted evidence (`graded`)
- Metric: Public evidence graded
- Implemented by: [`implementations/python/esoi/optimization/when_metrics_are_run/public_evidence/evidence_grading.py`](evidence_grading.py), [`implementations/python/evaluation/components/public_evidence/__init__.py`](../../../../evaluation/components/public_evidence/__init__.py), [`implementations/python/evaluation/components/public_evidence/broken/__init__.py`](../../../../evaluation/components/public_evidence/broken/__init__.py), [`implementations/python/evaluation/components/public_evidence/broken/trust_the_number.py`](../../../../evaluation/components/public_evidence/broken/trust_the_number.py), [`implementations/python/evaluation/components/public_evidence/cases.json`](../../../../evaluation/components/public_evidence/cases.json), [`implementations/python/evaluation/components/public_evidence/impls/__init__.py`](../../../../evaluation/components/public_evidence/impls/__init__.py), [`implementations/python/evaluation/components/public_evidence/impls/graded.py`](../../../../evaluation/components/public_evidence/impls/graded.py), [`implementations/python/evaluation/components/public_evidence/impls/live.py`](../../../../evaluation/components/public_evidence/impls/live.py) and 2 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Letter grades by weighted evidence | `public-evidence:graded` | Grades each candidate and dimension from the evidence rows by the visible weights table: a letter from A to D, the flags raised, and the one run of the repository's own that would settle it. | [`implementations/python/esoi/optimization/when_metrics_are_run/public_evidence/evidence_grading.py`](evidence_grading.py) | selected |
| A model summarizes the sources | `public-evidence:model-summary` | A model reads the reported results and writes a verdict per candidate in words. | no code yet |  |

## Metrics

- Public evidence graded (`metric-public-evidence`): leader `graded`, 11 of 11 cases

## Where to go next

- Up: [implementations/python/esoi/optimization/when_metrics_are_run](../README.md)
- Intent: [Implementations Chosen on Evidence](../../README.md)
- Repository: [top README](../../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
