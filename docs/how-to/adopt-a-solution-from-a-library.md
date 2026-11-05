# Adopt a solution from a library

Use this when your repository needs a job that a library's ESOI records already define, so you reference the solution instead of copying
its records. Why this is the form is in [Adopting solutions from a library](../explanation/adopting-solutions-from-a-library.md).

## 1. Choose the kind of record

For each job, ask: would a stranger's use of the library need this?

- Yes, and the library has it: **adopt** (steps 2 to 4).
- It is the library's job but needs your data: **specialize** (step 5).
- Only your application has it: **own**. Write full records as usual and stop here.

## 2. Name the library

In `esoi.toml`, say where the library's repository is. The name is yours to choose and is what the references use.

```toml
[adopts.hub]
repo = "../hub"                      # the library's repository (it has its own esoi.toml)
url = "https://example.org/hub/"     # optional: generated pages link here instead of to the relative path
```

## 3. Record the adoption

Add one row to the `solutions.csv` of the intent where the solution belongs. Fill only the id, the name and `adopts`; leave every field the
library defines empty.

```csv
solution_id,name,adopts
route-model-request,Route a model request,@hub/route-model-request
```

(Your file keeps all its usual columns; the others stay empty in this row.) The `adopts` column is a technical column, so it needs no
approval in `[records] approved_fields`.

## 4. Add your own arm, if you have one

An arm of yours that competes with the library's is a row in `implementations.csv` whose `solution_id` is the adopted solution, and its code
declares the library's solution id and follows its interface:

```python
@implementation("route-model-request", "our-tier-router")   # the library's solution id
class OurTierRouter:
    def route(self, request): ...
```

The adopted solution takes your own arms and metrics like any solution: list the arms in its `implementations` cell, name a metric in its
`metric_ids`, a port in its `interface_name`, and a component in `components.csv` may list its id in `solutions`. The checks that resolve a
solution id (S7, S11, S21, S26, S29) see it; only the words the library holds are not asked of you.

Then make the application's metric build on the library's with a `[builds_on]` table (see [Build a metric on a foundation](../explanation/a-metric-builds-on-its-foundation.md)),
so your arm is scored on the library's cases plus your own, in one number.

## 5. Specialize, when the library's solution needs your data

Write a full record in your own `solutions.csv` with a short vision of what your data adds, scope the role (`out_of_scope`, `delegates_to`
naming the adopted solution), and set `specializes` to the library's solution:

```csv
solution_id,name,specializes
route-for-our-customers,Route for our customers,@hub/route-model-request
```

## 6. Check and read the page

Run `esoi check --findings`. Rule S53 informs of an adoption that does not resolve, an adopted row that restates the library, an own
solution that says the same job as a library solution, and an arm that does not declare the library's solution id. Each finding says its
next action; waive one with a reason in `waivers.csv` when the difference is real.

Run `esoi check --write-docs` and open the intent's README: the adopted solution is a link to the library's page with the library's
description of it.

## When an own solution turns out to be general

Propose it to the library's owner as a solution record with its problems and ideals. When the library has it, change your record to an
adopted one and move your code in as an arm.
