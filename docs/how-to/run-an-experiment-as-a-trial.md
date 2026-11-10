# Run an experiment

What an experiment is: [experiments in ESOI](../reference/experiments-in-esoi.md). Keep it loose; skip any step that does not fit a qualitative exploration.

1. **Open it.** One row in `experiments.csv` at the intent: the name, the research question (the question or way of thinking), its
   owners (empty for your own), the start, the time or condition of reevaluation, what is in scope and what is outside scope for now,
   and `held_fixed`: the choices that are not re-decided until then (`subject = choice`). Set the status to `running`.
2. **Work inside it.** Keep attention in its scope and do not reopen what it holds fixed. Each review, trial, observation or
   interview is an investigation: a row in `investigations.csv` that names the experiment (`experiment_id`) and follows the
   [research standard](../reference/knowledge-search-standard.md), sized to what it decides; add its id to the experiment's `investigation_ids`.
3. **For a comparison of alternatives, fix the judgement before running.** The alternative is an implementation that is not
   `selected`; name the metric stage, the value expected (a solution milestone) and the value that rejects it (the stage's floor), and
   list them in `held_fixed`. A qualitative exploration states instead what will be observed, how, by whom and what would change one's mind.
4. **Reevaluate at the time** (`esoi.understanding.solution_consideration.experiments.due` lists what is past it; set the status to
   `reevaluating`). Fill `learned`; give each investigation item an `applied` entry; fill `changed` with the knowledge row, structure,
   priority or milestone it changed; set `decision` to `continue`, `change` or `end`.
5. **Close or continue.** For an alternative, `esoi select --promote` proposes the switch. For priorities, add, reorder or retire a
   milestone. For structure, add the problem, ideal, solution or alternative. Set the status to `ended` and name the next
   experiment in `next_experiment_id`, or, to continue, set the status back to `running` with the next date.
