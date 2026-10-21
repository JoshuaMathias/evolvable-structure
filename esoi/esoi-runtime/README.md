These are ESOI records (evolvable structure that optimizes intent): why this sub-intent exists, and its problems, solutions, implementations, ideals and metrics. This page is generated from the CSV files beside it by `esoi check --write-docs`; edit the CSV files, not this page.

# ESOI inside other people's running code

The esoi package is a dependency of other people's production code, which declares its alternatives gracefully and selects the best implementation while it runs.

This sub-intent arises as the implementation `implementation-selection:declarations` of its parent intent `esoi`. Opportunities: The Python package can become a runtime dependency inside other people's production code, not only a tool run on a repository: selection at run time, graceful declarations of alternatives (decorators, for example) and embedding without forking. That is a creative space beyond selecting an implementation by a table in one repository.

## Solutions

| Solution | Name | Selected | Metric |
|---|---|---|---|
| `runtime-selection` | Select an implementation while the program runs | declarations-and-cascade | Python selector cases |

## Implementations

| Implementation | Name | Where | Sub-intent |
|---|---|---|---|
| `runtime-selection:select` | Selector class and table | implementations/python/esoi/select.py |  |
| `runtime-selection:declarations-and-cascade` | Declarations in code with one cascade | implementations/python/esoi/runtime.py |  |

## Metrics

- `metric-runtime-selection`, Python selector cases: `esoi run select_an_implementation --impl live_selector`
