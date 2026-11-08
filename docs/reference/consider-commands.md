# Consideration commands

## `esoi spec prompt SOLUTION`

| Option | Meaning |
|---|---|
| `--task TEXT` | the change, candidate or request the pass considers |
| `--budget N` | the size budget in characters (default `[consider] budget`, else 24000) |
| `--with FILE` | a CSV of findings or candidates to join the prompt (repeatable) |
| `--json` | print `{solution_id, name, role, parent, children, text, chars, sections, omitted, digest}` |
| `--no-stale` | skip the check of which results describe older code (faster) |

Exit 1 for an unknown solution.

## `esoi consider TEXT`

| Option | Meaning |
|---|---|
| `--solution ID` | name the solutions instead of classifying the text (repeatable) |
| `--max N` | how many relevant solutions before their parents (default 5) |
| `--arm NAME` | `index_with_links` or `lexical_index` (default: the selected arm of Solution Relevance) |
| `--budget N`, `--with FILE`, `--no-stale`, `--cache FILE` | as above; `--cache` reuses the specification index |
| `--list` | one line per prompt instead of the JSON |

The JSON is `{input, arm, index_digest, budget, prompts}`; each prompt is the dict of `spec prompt --json` plus `score` and
`reached_by` (the records that reached the solution). `role` is `solution` or `parent`.

## Python

| Call | Returns |
|---|---|
| `solution_prompt.load(config, extra=(), stale=True)` | the network: records, results, graded evidence, declared finding files |
| `solution_prompt.prompt(network, sid, task="", budget=24000, role="solution")` | one prompt as above |
| `solution_prompt.parent_of`, `children_of`, `dependencies_of`, `dependents_of` | the edges of one solution |
| `fan_out.classify(network, index, text, limit=5, arm="")` | solutions then parents, each `{solution_id, score, via, role}` |
| `fan_out.consider(network, index, text, limit=5, budget=24000, arm="", only=())` | the JSON of `esoi consider` |
| `relevance_cases.mine(config, registry)`, `build(config, registry, hand)` | relevance cases from git history and hand-labelled ones |
| `relevance_cases.score_case(fn, case)`, `aggregate(rows)` | the shared scorer: recall, precision, misses |

Modules: `esoi.understanding.solution_consideration` and `esoi.understanding.solution_relevance`.

## Configuration

```toml
[consider]
budget = 24000

[[consider.records]]
file = "path.csv"
kind = "finding"         # free label; "finding" and "candidate" are checked by S60
id = "finding_id"        # default: the first column
solution = "solution_id" # default: solution_id, solution_ids or solution when present
candidate = "candidate"  # default: candidate when present
results = ""             # a column that cites recorded results
```

## Rule S60

A finding or candidate in a declared file names one solution, and cites the recorded results of that solution when it has any; the
file has a column that names the solution. Waive one row by its id, or the file by its path.
