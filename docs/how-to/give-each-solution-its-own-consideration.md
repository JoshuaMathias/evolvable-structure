# Give each solution its own consideration

Why this exists: a solution is an area that deserves its own depth of focus, and its records are its durable memory. One broad pass
of AI that judges a change or an outside candidate across a whole project reads none of them, and can rate strongest a candidate
whose arm already lost on the solution's own cases. The fix is one pass per relevant solution, each given a prompt that the
solution's network of records forms, with nothing written per solution.

## One solution's prompt

```bash
esoi spec prompt cards-from-files --task "Should we adopt this graph tool for cards?"
esoi spec prompt cards-from-files --json --budget 12000      # the text, its sections by tier and what the budget cut
```

The prompt holds, closest and most decision-relevant first:

1. the solution's definition (purpose, approach, out of scope, interface, milestones, Knowledge), every recorded result of its
   implementations (newest run each, best first, stale ones said, never hidden) and its selection (the selected arm, the layer of
   the selection cascade that runs it, what the metric's cascade chooses);
2. the findings and candidates queued against it, how its children combine (for a solution with children: the child intent's
   coherence and diagram), its metric and cascading conditionals, its problems and ideals, the public evidence and priors kept for
   its implementations, and its implementations;
3. its parent briefly, its children and dependencies by purpose, interface and selected arm;
4. its dependents, by what they rely on.

It fills a size budget in that order (`--budget`, else `[consider] budget` in `esoi.toml`, else 24000 characters). A section that
does not fit is cut at a line and named in the JSON's `omitted`.

## One prompt per relevant solution

```bash
esoi consider "A deterministic code graph with hybrid retrieval, for memory and cards" --list
esoi consider "..." > prompts.json                            # one prompt per solution, then one per parent level
esoi consider "" --solution cards-from-files                  # name the solutions instead of classifying the text
```

Solution Relevance picks the solutions (the selected arm, or `--arm lexical_index`), and the parent of each is added after them so
the scope above gets its own pass. Run one pass per prompt in `prompts.json`; the library calls no model.

From Python:

```python
from esoi.structure.intent_registry import config
from esoi.understanding.solution_consideration import fan_out, solution_prompt
from esoi.understanding.spec_search import spec_index

cfg = config.load(".")
network = solution_prompt.load(cfg)                 # records, results, evidence and declared finding files, read once
found = fan_out.consider(network, spec_index.build(cfg), "the change or candidate")
for item in found["prompts"]:
    run_one_pass(item["text"])                      # your model call
```

## Knowledge: offered, chosen by the situation

Which knowledge bears on a pass depends on the request, so the prompt holds the solution's stable part and its knowledge items come
back beside it as candidates (`--knowledge candidates`, the default; `--json` shows them). Pick the ones that bear with your own
retrieval (or `knowledge.select(items, task)`), and append them; `--knowledge ranked` writes all of them in, in a fixed order, when
there is no retriever. The records and commands are in [knowledge records](../reference/knowledge-records.md).

## Let findings and candidates join the prompt

Declare each file of findings or candidates once:

```toml
[[consider.records]]
file = "registry/findings.csv"
kind = "finding"            # "finding" and "candidate" rows are checked by rule S60
solution = "solution_id"    # the column that names the one solution a row is rated against
candidate = "candidate"     # a candidate that names an implementation also reaches its solution
```

`--with FILE` adds a file for one run. Rule S60 then asks that every row names one solution (one row per solution, never one row
across several), and that a row about a solution with recorded results cites them (the results log's name in its text, or a
`results` column).

CSV files kept in a solution's own records folder that are not record files (priors, a local registry) join its prompt with no
declaration.

## Measure it

`esoi run solution_consideration --impl network_tiered` checks that the deciding records reach the pass on a synthetic repository
shaped like the incident above and on this repository's records; `definition_only` is the baseline of the solution's record alone.
`esoi run consideration_verdicts --impl network_prompt_model` is the paid stage: a cheap model gives a verdict on a matter whose
deciding record is held only in the network, once with the network prompt and once with the record alone (`record_alone_model`).
`esoi run solution_relevance --impl lexical_index` scores the classification on cases mined from git history and written by hand:
each case is graded by its F2 score (recall weighs four times precision) and passes when no needed solution is missed;
`model_classifier` and `lexical_then_model` are the cheap-model arms. Model arms need `ESOI_MODEL_COMMAND` and `ESOI_MODEL`
(`esoi/metric-run-policy.md`); the library builds the prompt and reads the reply (`relevance.classification_prompt`,
`relevance.parse_ids`, `relevance.model_arm(answer)`), and the caller supplies the model. Another repository builds its own case set with `esoi.understanding.solution_relevance.relevance_cases.mine` and shares the
scorer (see [the commands](../reference/consider-commands.md)).
