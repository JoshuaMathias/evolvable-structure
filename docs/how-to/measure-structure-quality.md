# Measure structure quality

Why: [code quality is structure quality](../explanation/code-quality-is-structure-quality.md). Steps:

1. **Run stage one** on any Python project, offline and read-only:
   ```
   esoi structure-quality path/to/project
   ```
   It prints the balanced number, each dimension with its weight, and the worst offenders of each. It is advisory and always exits 0. A repository
   that has an `esoi.toml` also gets the flow dimension from its coherence gate.
2. **Run stage two** to add co-change from git history to the coupling dimension:
   ```
   esoi structure-quality --stage 2 path/to/project
   ```
   Files in different solutions that changed together in at least five of the last 400 commits, and in at least 80 percent of the commits of the
   less often changed of the two, with no import between their solutions, are listed as hidden coupling.
3. **Read the weak dimensions.** A dimension under 0.6 is named. Fix the worst offenders at their source: make an arm define its Protocol's
   methods, call another solution through its interface, write copied code once, split a part at a seam of its own job (not into fragments: the
   coupling and reuse dimensions charge for that), add one contract test that runs every arm.
4. **Turn on the rules** to see the same findings in `esoi check --findings`. In `esoi.toml`:
   ```
   [rules.S54]
   enabled = true
   ```
   S54 is scope, S55 size and cohesion, S56 coupling, S57 reuse, S58 public surface, S59 behavior preserved (flow fidelity is S38). Each finding
   says its next action; waive one as the path or unit it opens with.
5. **Tighten, never loosen.** A library names the consumers it must not mention, and a project may tighten a budget, from code:
   ```python
   from esoi.structure.structure_quality import assess
   from esoi.structure.structure_quality.balance import Budgets

   report = assess.assess("path/to/project", stage=1, budgets=Budgets(consumers=("my_app",)).tightened(function_lines=60))
   print(report["score"], report["flagged"])
   ```
   The weights are fixed in the library; a consumer's metric names it with `[builds_on]` and adds only its thresholds and cases.

The cases that keep the scorer honest are in `implementations/python/evaluation/components/score_structure_quality/`; run them with
`esoi run score_structure_quality --impl balanced_static`. The expert review arm is paid and never runs without approval.
