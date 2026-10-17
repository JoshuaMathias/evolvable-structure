# Related frameworks and designs

ESOI did not appear in a vacuum. Many people building with AI agents have reached pieces of the same shape: write the
intent down, keep alternatives, measure them, let the measurement choose. This page maps that neighbourhood honestly.
For each group it says what the work is, what it shares with ESOI, where it differs, and what ESOI could borrow. Nothing
here is a claim that these frameworks are ESOI; most cover one or two of its five record types and none, as far as we
could verify, covers all of them together with the structure itself evolving. The author's own definitions stay the
authority ([from-the-skill.md](from-the-skill.md)). The research record, with quotes and what we could not verify, is
[kept with the skill](../../skill/evolvable-structure/sources/agentic_frameworks.md).

## Layered models of trustworthy agents

**The Agentic Integrity Stack** ([Sarah Payne](https://www.sarahpayne.ai/the-agentic-integrity-stack)) is a design
checklist of six layers for agents that act autonomously but stay controllable: scoped purpose, bounded tool access,
planning and replanning, fallback and escalation, structured memory, and interrupt logic. It adds three mechanisms:
constraints that adapt only with human or policy approval, fixed cross-agent authority, and checking the real end state
against verifiable criteria. The author says it is not yet tested at production scale.

It shares ESOI's insistence on a scoped purpose, and its outcome reconciliation (compare the real state with checkable
conditions) is close to ESOI's preference for the problem solved in the wild over task completion. Its split between
what adapts (constraint levels) and what never does (purpose, interrupts, fallback) is the same decision ESOI asks you to
make about what is stable and what is changeable. It differs in being a diagnostic for one agent's runtime behaviour, with
no alternatives or metric-driven selection. ESOI could borrow its "working signal" per layer, a one-line observable test
that a layer works, and its rule that a safeguard layer is not tuned by the same loop it guards.

## Spec-driven development and context files

**GitHub Spec Kit** ([repo](https://github.com/github/spec-kit)) moves from a project constitution to a specification,
a plan, tasks and implementation: "Define what and why before deciding how to build it." **Kiro**
([specs](https://kiro.dev/docs/specs/)) generates requirements, design and task files per feature.
Birgitta Bockeler's [survey](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) separates spec-first
(spec guides one task), spec-anchored (spec persists and evolves) and spec-as-source (humans edit only the spec), and
finds the tools are mostly spec-first. **AGENTS.md** ([agents.md](https://agents.md)) is an open format for agent
instructions where the nearest file to the edited code wins.

These share ESOI's "why and what before how". AGENTS.md precedence resembles ESOI's rule that an application states only
what differs. They differ in three ways: a spec is one document, not a network of problems, ideals and solutions; there is
no second implementation to compare, so the spec cannot choose anything; and review stays on the generated artifacts, the
burden ESOI wants lifted. Bockeler's note that regenerating from one spec gave different results is the case for ESOI's
metric: a spec alone cannot say which output is better. ESOI could borrow the spec-first, anchored, source vocabulary to
label how binding each record is.

**Context engineering** ([Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents))
is "the smallest set of high-signal tokens" that makes the outcome likely, with just-in-time retrieval and compaction.
It shares ESOI's reading only what is necessary at a given moment. It does not decide which context strategy is best; ESOI
would treat each strategy as an implementation of a context-assembly solution.

## Eval-driven development and metric-selected implementations

**DSPy** ([paper](https://arxiv.org/abs/2310.03714), [repo](https://github.com/stanfordnlp/dspy)) is the closest
technical cousin. A declarative module states what a step does, and a compiler optimizes the pipeline toward a metric
you supply. Signature as interface, optimizer-chosen prompt as implementation, metric as authority: that is
solution, implementation and metric in code. **GEPA** ([paper](https://arxiv.org/abs/2507.19457)) evolves prompts by
reflecting on trajectories and keeping a Pareto frontier. **TextGrad** ([paper](https://arxiv.org/abs/2406.07496))
propagates natural-language feedback to improve components, and **EvoPrompt**
([paper](https://arxiv.org/abs/2309.08532)) evolves prompt populations scored on a development set. All of these search
the implementation space of one given interface. They do not record the problem or the ideal, do not say when to split an
interface, and do not make the metric itself a replaceable solution. ESOI could borrow Pareto selection when two ideals
(cost and accuracy) pull apart, instead of forcing one number.

**Evaluation harnesses.** [Inspect](https://inspect.aisi.org.uk/) defines an evaluation as dataset, solver and scorer.
[Promptfoo](https://www.promptfoo.dev/docs/intro/) puts prompts, test cases and metrics in a matrix "to choose the best
model and prompt". Anthropic's [guide to evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
separates capability evals (start low) from regression evals (near 100%) and says to calibrate model graders against
humans. Hamel Husain's [essay](https://hamel.dev/blog/posts/evals/) says the same: evals set iteration speed, and judges
need their own evaluation. LLM judges agree with humans over 80% of the time in
[one study](https://arxiv.org/abs/2306.05685), with known position and verbosity biases. These are the machinery of an
ESOI Metric. They differ in being a practice, not a structure: nothing says which solution a result belongs to or that the
winner should run automatically. ESOI could borrow the capability-to-regression graduation and the saturation warning.

## Self-improving and evolutionary systems

**AlphaEvolve** ([paper](https://arxiv.org/abs/2506.13131)) edits code over many iterations using evaluator feedback.
**OpenEvolve** ([repo](https://github.com/algorithmicsuperintelligence/openevolve)) is an open version with
evaluator functions, quality-diversity grids and island populations. The **Darwin Godel Machine**
([paper](https://arxiv.org/abs/2505.22954)) keeps an archive of agents and rewrites its own code, validating by benchmark
rather than proof. **ADAS** ([paper](https://arxiv.org/abs/2408.08435)) has a meta agent program new agents from an
archive. **AFlow** ([paper](https://arxiv.org/abs/2410.10762)) searches workflows with Monte Carlo Tree Search.
**Eureka** ([paper](https://arxiv.org/abs/2310.12931)) evolves reward code, and **Voyager**
([paper](https://arxiv.org/abs/2305.16291)) keeps a growing library of executable skills.

They share the loop: propose alternatives, score with an evaluator, keep the winners, with an archive of past
alternatives. That is ESOI's implementations and metric, automated. They differ in having no recorded intent: the
evaluator is fixed and trusted, and the search runs inside one task. ESOI's humility principle covers what they leave
open, that the metric is an approximation, and the evidence agrees: pushing a proxy too hard lowers true performance
([Gao et al.](https://arxiv.org/abs/2210.10760)). ESOI could borrow the archive (keep losing alternatives as stepping
stones, not only the selected one) and diversity-preserving selection. Ford, Parsons and Kua's fitness functions are
covered in the earlier research note.

## Routing, experiments and flags

**RouteLLM** ([paper](https://arxiv.org/abs/2406.18665)) trains routers that choose a stronger or weaker model per query,
reporting cost cuts of more than half on some benchmarks without a quality loss. [Not Diamond](https://www.notdiamond.ai/)
sells routers trained on a customer's own evals (its savings figures are marketing claims). Fowler's
[feature toggles](https://martinfowler.com/articles/feature-toggles.html) include experiment toggles that hold a
configuration steady long enough for a statistically meaningful comparison.

This is automatic selection by metric, but per request. ESOI selects one implementation per solution from a recorded
comparison, and routing shows when "best" varies by input, which is the split test in [when-to-split.md](when-to-split.md).
ESOI could borrow the router as a fourth kind of selection and the toggle rule to leave a configuration alone while it is
measured.

## Oversight and governance

The [NIST AI RMF](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) has four functions (Govern, Map, Measure,
Manage). It asks that human oversight processes be "defined, assessed, and documented", that risks which cannot be
measured be documented, and that independent assessors take part. Weak-to-strong work
([Burns et al.](https://arxiv.org/abs/2312.09390)) and scalable oversight
([Bowman et al.](https://arxiv.org/abs/2211.03540)) ask how weaker evaluators can supervise stronger systems, and
Constitutional AI ([Bai et al.](https://arxiv.org/abs/2212.08073)) lets a short list of human principles steer AI
feedback. Mitchell et al. ([paper](https://arxiv.org/abs/2502.02649)) argue that risk rises with autonomy.

All of these place human attention at principles and measurement, not at each output, which is ESOI's fourth principle:
humans need only review metrics, not implementations, though they can still add value to implementations. The difference
is that these are about risk, while ESOI is also about progress. ESOI could borrow the NIST habit of recording what the
metric cannot measure.

## Comparison

| Framework | Closest ESOI type or principle | Shares | Differs | Borrow |
|---|---|---|---|---|
| Agentic Integrity Stack | Solution scope, ideals | Scoped purpose, state-vs-process check | One runtime, no alternatives | Working signal per layer, guarded layers not self-tuned |
| Spec Kit, Kiro | Problem, Solution | Why and what before how | No alternatives, review on artifacts | Spec-first, anchored, source labels |
| AGENTS.md | Principle 9, 12 | Nearest file wins, state the difference | Instructions, not intent | None needed |
| DSPy, GEPA | Solution, Implementation, Metric | Interface, metric-chosen implementation | No problems or ideals, fixed metric | Pareto selection |
| Inspect, Promptfoo, evals guides | Metric | Cases, scorers, graders | No selection or ownership | Graduation to regression, saturation |
| AlphaEvolve, DGM, ADAS, AFlow | Implementation, Metric | Evaluator-selected variants, archive | Intent unrecorded, evaluator trusted | Keep losers as an archive |
| RouteLLM, toggles | Principle 4, when to split | Automatic choice by metric | Per request, not per solution | Router arm, frozen config while measured |
| NIST AI RMF, scalable oversight | Principles 4, 6, 7 | Humans at the measurement level | Risk focus, not progress | Record the unmeasurable |

## What ESOI adds

From this comparison, ESOI's contribution is the combination, not any single idea. Optimizers and evolutionary systems
choose among implementations but take the interface and the metric as given. Spec tools and context files record intent
but compare nothing. Eval tools measure but do not own the selection. Oversight frameworks place the human at the
metric but do not say what the metric is measuring. ESOI ties the five records into one network, so that a problem leads
to an ideal, a solution, rival implementations and a metric that picks one, and it makes the metric and the structure
solutions that can themselves change. We could not verify that this full combination is absent elsewhere; it is the
claim the sources support so far.
