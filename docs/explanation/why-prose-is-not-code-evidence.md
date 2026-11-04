# Why prose is not evidence that code uses a solution

The coherence check holds the paragraph to the code: "the paragraph matches how solutions relate in the code". Evidence must
therefore come from what the code does. A docstring or comment that names another solution says what a person wrote, not what
runs, and writing one is the cheapest way to raise a precision score without changing anything. So the check reads the syntax
tree and counts a mention only in executable code (an identifier, attribute, import, annotation, or a string used as a value).
Prose strings, docstrings and comments are left out. A relation that is real shows up in the code when it is wired through an
import, a typed need or a resolve call; a relation that only appears in prose is either missing wiring or not a relation, and the
records should say which. See [Declare a solution's interface](../how-to/declare-a-solutions-interface.md).

Lift is held to the same honesty. It compares how often the evidence fires on recorded edges with how often it fires on pairs
that are not edges, so it is only defined for an intent that records edges. A grouping of independent solutions has none; the
check reports "n/a (no recorded edges)" instead of inventing a number or failing a limit that has nothing to measure. An intent
that does record edges is never excused: a lift of 0.0 still fails `min_lift`. A limit that suits one intent is written in that
intent's own `[rules.S38.floors.<intent-id>]` table, so it is visible, reviewed by S39, and does not loosen every intent.

## Whose code a line is, and when an import counts

A module that several solutions share (esoi's `interfaces.py` holds the arms of thirty-three of them) says nothing about one
solution as a whole. The check therefore attributes evidence per solution: only the classes a solution declares with
`@implementation` or `@solution` count for it, and importing the shared file counts only when the import names the used
solution's class. Before that, every pair of those thirty-three named each other (881 of 1079 non-edges showed strong evidence,
lift 1.14), so a precision of 1.0 meant nothing.

The rules that decide what counts as strong evidence of "A uses B", in the order the check tries them:

1. **E1** a module of A imports a module of B (at module level or lazily inside a function: an import is executable code wherever it stands) (a module B shares with other solutions counts only when the import names B's class).
2. **E2** executable code of A names B's id or interface class (identifier, attribute, import, annotation, decorator or call
   argument, or a string used as a value). Docstrings, comments and bare string statements never count.
3. **E3** A's implementation takes a parameter typed with B's interface, a need the Assembler injects.
4. **E4** a module the ownership map (`components.csv`) gives to A imports a module it gives to B. Both modules must be owned
   by that one solution each (a module several solutions own does not say which is meant), the importer may be shared with
   others only if A is among its owners, the package `__init__` never counts, and the chain is one import long: A's code
   imports A's own module, which imports B's. The ownership map and the import are both records of fact: a name in a docstring
   or comment on either side changes nothing.

5. **E5** (documents) a markdown link or include in a document only A owns to a document only B owns. A solution that is a
   document has no import to follow, so the evidence is the link a reader follows: an inline link, an image, a reference
   definition or an include directive, resolved from the linking document's folder. A document is a solution's when
   a `components.csv` row names it in its `documents` column (`path=solution-id`, see
   [Component documents](../reference/component-documents.md)) or the solution's selected implementation names it as its `filepath`. The same
   discipline as the code rules holds: a link shown inside a fenced block, inline code or an HTML comment is not a link, a path
   mentioned in prose is not a link, URLs and bare anchors point nowhere in the project, and a document several solutions own
   (a whole `docs/**` folder) counts on neither side. An edge whose ends have no module is checkable when both own a document.

Weak evidence (W1 to W3) is reported and never counts toward precision.

E4 was added after measuring it against the alternatives on three repositories (esoi, the hub of hubs and quest-ai-runner), each
by the base rate (the share of pairs that are not recorded edges and still show strong evidence) and the lift (precision over base
rate). Counting any import of a module the used solution owns raised esoi's base rate to 0.048 and the hub's to 0.178, so it was
rejected. Following a call into a helper function of the same module added nothing to precision and was dropped. E4 as written raised the
base rate of esoi from 0.006 to 0.022 and quest-ai-runner's from 0.023 to 0.034, left the hub's at 0.017, and kept lift above
20 on all three. The remaining non-edge pairs it finds are mostly relations the records leave unstated, which is what a base rate
is for.

### What the check still cannot see in esoi, and why

With E4, 22 of esoi's 43 recorded uses edges show strong evidence. The other 21 are not wrong; they are of two kinds, and no
evidence rule that keeps docstrings out could see them:

- **Seven are in the code but behind a module several solutions own.** `structure-check` runs the rules through `check.py` and
  `rules/`, which `readable-records`, `structure-rules` and `ownership-map` also own; `implementation-selection` reaches
  `runtime-selection` and `assemble-by-name` through `runtime.py`, `lock.py` and `entry.py`; `assemble-by-name` builds on
  `runtime-selection` in `assemble.py`, while its recorded arm is in `interfaces.py`. `measurement-harness` runs baseline arms as
  data (`discriminating-cases`) and its stages follow a policy written in `metric-run-policy.md` (`when-metrics-are-run`).
- **Fourteen are a composition of documents, commands and judges.** `apply-esoi` takes up `the-standard`, `esoi-for-ai`,
  `promote-the-winner`, `keep-metric-record`, `local-application-index`, `consumer-check` and `implementation-selection`;
  `the-standard` gives `the-steps`, `docs-and-templates` and `skill-distribution`; `esoi-for-ai` gives an agent
  `behave-by-esoi` and `esoi-behaviour-judge`; `the-steps` is `follow-the-steps`; `structure-rules` keeps rules while
  `structure-budget` says they pay. The paragraph says what the written documents and commands do; the Python arms in
  `interfaces.py` are one-fact probes of them (a line count, a number of cases), so they do not call each other. When a probe
  genuinely depends on another solution it should say so in code with a typed need, as `esoi-behaviour-judge` now does
  (it reads its cases through `judge-esoi-behaviour`); until then the floor records what is seen.

Document edges are readable when the records say which documents a solution owns. esoi's `components.csv` names, in `documents`,
the guides and skill files that belong to thirteen of its solutions. Seven document edges show a real link in those documents:
`apply-esoi` to `implementation-selection` and `local-application-index` (links the guide already had), to `the-standard`,
`esoi-for-ai`, `keep-metric-record` and `consumer-check` (a short paragraph of links added to `apply-with-tools.md`, each pointing a
reader to the page that explains that part), and `measurement-harness` to `when-metrics-are-run` (the harness's cassette how-to
already linked the policy; the two pages were not yet recorded as theirs). Eleven stay unseen on purpose, each for a stated reason:

- `apply-esoi` to `promote-the-winner`, `measurement-harness` to `discriminating-cases`, `structure-rules` to `ownership-map` and
  `structure-budget`, and `structure-check` to `structure-rules` have no document of their own on the used side: they are
  compositions of commands and rules whose arms are code, so a link has nothing to point at, and the records are not wrong.
- `esoi-for-ai` to `behave-by-esoi` and `esoi-behaviour-judge` are described by one page, `esoi-for-ai.md`, which is the page of the
  composition itself, so no second page links to or from it.
- `the-standard` to `docs-and-templates`, `skill-distribution` and `the-steps`: the standard document is generated by
  `esoi template sync` from the author's skill, so it cannot carry a hand-written link.
- `the-steps` to `follow-the-steps`: the steps file lives in the skill folder, which is published and copied on its own, so it
  must not link into `docs/`. The guide `apply-by-hand.md` links to the steps file, which is the opposite direction; whether the
  record's direction should be reversed is a question about the spec, left open rather than changed to fit a link.

A floor is a measurement. `esoi.toml` holds esoi's at 0.725 and the runtime sub-intent's at 0.0 (with `min_lift = 0.0`, written
there with its reason), and each rises when a composition is typed in code.
