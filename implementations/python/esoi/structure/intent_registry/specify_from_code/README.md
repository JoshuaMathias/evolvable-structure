# Specify from the Code

**Purpose:** Keep the records of a solution and its alternatives in step with the code that declares them, and create a new solution in one command.

Breadcrumb: [Top](../../../../../../esoi/README.md) > [A Project's Records and Code as One Structure](../../README.md) > [Intent Registry](../README.md) > Specify from the Code

Part of [Intent Registry](../README.md)

## Specify from the Code (`specify-from-code`)

- Out of scope: Writing the intent itself, and importing the code it reads.
- Entry call: `esoi.run("specify-from-code", '.')`
- Selected implementation: Declarations read from the code, rows synced (`declarations-and-sync`)
- Metric: Declaration sync
- Implemented by: [`implementations/python/esoi/__main__.py`](../../../__main__.py), [`implementations/python/esoi/command_table.py`](../../../command_table.py), [`implementations/python/esoi/structure/intent_registry/admit.py`](../admit.py), [`implementations/python/esoi/structure/intent_registry/specify_from_code/declarations.py`](declarations.py), [`implementations/python/esoi/structure/intent_registry/specify_from_code/interface.py`](interface.py), [`implementations/python/esoi/structure/intent_registry/specify_from_code/newsolution.py`](newsolution.py), [`implementations/python/esoi/structure/structure_check/rules/declarations.py`](../../structure_check/rules/declarations.py), [`implementations/python/evaluation/components/per_case.csv`](../../../../evaluation/components/per_case.csv) and 25 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Declarations read from the code, rows synced | `specify-from-code:declarations-and-sync` | The code declares a solution and its alternatives with decorators. The declarations are read without importing the code, what the records lack is reported (rule S30), and the missing rows are written with only what the code knows. One command writes the records, a code skeleton and an evaluation folder together for a new solution. | [`implementations/python/esoi/structure/intent_registry/specify_from_code/interface.py`](interface.py) | selected |
| Records kept by hand | `specify-from-code:hand-kept-records` | A person adds the alternative to the code and writes its records separately; a check, if there is one, only reports the drift. | no code yet |  |

## Metrics

- Declaration sync (`metric-declaration-sync`): leader `live_declarations`, 14 of 14 cases

## Problems

- Records copy the code (`prob-records-copy-the-code`): The records repeat what the code already says: which alternatives of a solution exist, the file each lives in, and an interface's signature.

## Where to go next

- Up: [implementations/python/esoi/structure/intent_registry](../README.md)
- Intent: [A Project's Records and Code as One Structure](../../README.md)
- Repository: [top README](../../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
