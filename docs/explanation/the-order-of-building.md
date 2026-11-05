# The order of building with structure

Structure comes before code, and the top of the hierarchy comes before the bottom. This page gives the whole order, from the first
intent to the loop of continual improvement. It applies to anything ESOI structures (specifications, processes, documents, business
offerings, how an AI behaves); code is one case. Each step says what it settles, so that the next step has something firm to stand on.

## The order

1. **Define and refine the hierarchy of intents and solutions, with vision statements.** The hierarchy decides the scope of each
   category: what belongs under which intent, which solutions are containers for which jobs, and what is out of scope. Write each
   intent's vision statement here, one short sentence about the whole concept. Problems and ideals come with it, because they say why
   each solution exists. Merge, split and move solutions until each has one purpose.
2. **Write each solution's interface and the intent's coherence paragraph together, and refine them against each other until
   everything is accounted for.** The interface says what the solution takes and returns and who is responsible. The paragraph says,
   in names, how the intent's solutions connect and implement the parent solution. Writing one shows what is missing from the other: a
   step in the paragraph with no interface, an interface the paragraph never uses, a solution that nothing calls. Repeat until every
   solution is in the paragraph and every call in the paragraph has an interface. The interface exists before any implementation does;
   until one does, the step is reported as pending. Judge the scoping here, before any code exists, with these questions: does each
   interface do one job, and do all its alternatives serve that job at one level of specificity? Does any call reach past an interface into
   another solution's inside? Does any solution name a consumer, or does the dependency run both ways? Is any step written twice, so that two
   interfaces would hold the same arithmetic? Is there one contract that every alternative must keep? These are the dimensions of
   [Structure Quality](code-quality-is-structure-quality.md), which measures them on code once there is some.
3. **Create the diagram.** Draw it from the finished paragraph, so that the picture shows the same relationships the words and the flow
   state.
4. **Define the metrics.** Each solution gets the metric that says what it is for: one balanced number at rising fidelity, with its
   case sources, and a metric built on a library's metric where one exists.
5. **Consider which implementations to build.** Use each solution's first-stage metric to weigh ideas before building them. The free
   first stage shows which alternatives deserve the cost of an implementation, so the list is chosen by measurement, not by who had
   the idea.
6. **Implement the ones worth implementing.** Doing so may show that a solution's interface should change; change the interface and the
   paragraph together, and keep the records true to them. A solution's implementations share one purpose, and the flow above them is
   already written, so each implementation slots into a place that exists.
7. **Run the metrics after each implementation and the implementations that depend on it are complete.** Not before: a result on
   half-built code describes nothing. The result decides the selection.
8. **Loop.** New technologies, new cases, changed circumstances and what implementation teaches feed back into any earlier step: a
   better alternative is considered (step 5), an interface is refined (step 2), a solution is merged or moved (step 1). Improvement
   is continual, and the structure is what keeps it cheap.

## Why this order

Each step settles what the next one needs. The hierarchy fixes scope, so the interfaces and paragraph describe the right set of
solutions. The interfaces and paragraph fix the flow, so metrics measure a solution for the job it has in the whole. The metrics decide
which implementations are worth building, and implementations are measured when they are complete, so a selection rests on evidence
about the finished thing.

Putting visions, paragraphs or diagrams after the code reverses the dependency. The code then decides the structure, and the intent
has to describe whatever happened to be built.

## Where each step is done

| Step | Where |
|---|---|
| 1 | `intent.csv` (vision statement), `problems.csv`, `ideals.csv`, `solutions.csv`: [intents and sub-intents](intents-and-sub-intents.md), [when to create a sub-intent](when-to-create-a-sub-intent.md), [a solution holds alternatives of one job](a-solution-holds-alternatives-of-one-job.md), [scope the role of a solution](../how-to/scope-the-role-of-a-solution.md) |
| 2 | `interface.py` beside each solution and the `solution_coherence` field of `intent.csv`: [start from the flow](../how-to/start-from-the-flow.md), [declare a solution's interface](../how-to/declare-a-solutions-interface.md); rule S50 reads the code evidence |
| 3 | `solution_diagram` of `intent.csv`, generated with `esoi diagram` |
| 4 | `metrics.csv` and the cases: [what a metric includes](what-a-metric-includes.md), [a cascade runs one criterion](a-cascade-runs-one-criterion.md), [a metric builds on its foundation](a-metric-builds-on-its-foundation.md) |
| 5 | [The first stage needs no model](first-stage-needs-no-model.md), [why a new technology needs a decision, not a slot](admitting-a-technology.md) |
| 6 | `implementations.csv` and the code beside it: [declare, call, measure, promote](graceful-selection.md) |
| 7 | `esoi run`, with the approvals in [when metrics are run](when-metrics-are-run.md) |
| 8 | [Choosing by metric](choosing-by-metric.md) and the same steps again |

An application that adopts a library's solutions follows the same order for its own and specialized solutions; adopted ones are already
done at the library ([adopting solutions from a library](adopting-solutions-from-a-library.md)).
