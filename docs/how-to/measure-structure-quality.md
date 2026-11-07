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
3. **Compare before and after a restructuring.** Every merge, split, adoption, interface change or moved module is an alternative structure, so measure it
   as one: run step 1 before, make the change, then
   ```
   esoi structure-quality --compare <before> <after> [path-to-the-repository]
   ```
   Each side is a folder or a git reference (a commit, branch or tag) of the repository; a reference is checked out into a temporary worktree that is
   removed afterwards, and files the two sides share are read once. It prints the balanced number and each dimension before and after (and the number over
   the dimensions measured on both sides, so a dimension that appears or disappears cannot move the comparison), the offenders fixed and introduced, and
   the per-solution scope and per-unit coupling deltas. Keep the change only if the number holds or rises; when it falls, state in the commit what the
   number does not see and why the structure is better. From code: `from esoi import compare_structure_quality`. `--fast` leaves the flow dimension
   unmeasured (it reads the records and takes most of the time on a large project); the report says which dimensions were measured.
4. **Read the weak dimensions.** A dimension under 0.6 is named. Fix the worst offenders at their source: make an arm implement every member of its Protocol with matching parameters and a real body, merge a solution whose arms only pass each call on into the one they call, call another solution through its interface, move a name that only one unit takes out of the shared kernel and into that unit, write copied code once, split a part at a seam of its own job (not into fragments: the
   coupling and reuse dimensions charge for that), add one contract test that runs every arm.
5. **Turn on the rules** to see the same findings in `esoi check --findings`. In `esoi.toml`:
   ```
   [rules.S54]
   enabled = true
   ```
   S54 is scope, S55 size and cohesion, S56 coupling, S57 reuse, S58 public surface, S59 behavior preserved (flow fidelity is S38). Each finding
   says its next action; waive one as the path or unit it opens with.
   What S57 counts as copied: a file's tokens (names, numbers and strings reduced to their kind; imports, docstrings, constant tables, dataclass
   fields, constant registration decorators and Protocols left out) are matched in windows of 30 against every other file, and the matching windows
   merge into stretches. A stretch counts only when it is at least 40 tokens (about four lines) and holds at least three tokens that decide, loop or
   compute (`if`, `for`, `and`, a comparison, arithmetic): a shared signature, a dict of attributes or an argument parser is shape, not logic written
   twice. On this repository that took the copied share from 7.8 to 0.5 percent of the code, yet a function of seven lines copied into six files
   and a 30-line block copied once are both still found (`tests/test_structure_quality.py`). The two minimums are budgets (`clone_run`,
   `clone_logic`); a project may tighten them, never loosen them.
6. **Tighten, never loosen.** A library names the consumers it must not mention, and a project may tighten a budget, from code:
   ```python
   from esoi.structure.structure_quality import assess
   from esoi.structure.structure_quality.balance import Budgets

   report = assess.assess("path/to/project", stage=1, budgets=Budgets(consumers=("my_app",)).tightened(function_lines=60, complexity=8, kernel_instability=0.1))
   print(report["score"], report["flagged"])
   ```
   The weights are fixed in the library; a consumer's metric names it with `[builds_on]` and adds only its thresholds and cases.

## How to read the report

- **The first line** is the number, where it sits against the reference line, and how many files and units were read. Compare it only with the same
  repository at another commit (`--compare`), or with another repository measured the same way (both `--fast` or neither), because a dimension that is
  not measured shares its weight out over the others.
- **`measured` and `not measured`** say which dimensions the number rests on. `--fast` drops flow; a project with no solution of two or more arms has no
  behavior to measure. A number over five dimensions is not the same number as one over seven.
- **Each dimension line** gives its score, its weight and its parts. The parts are what moved: `function_lines_within_budget` falls with lines over the
  budget, not with the count of long functions; `cross_calls_through_entries_or_kernel` counts imports of the shared kernel as clean, and the note
  after it names the kernel modules, so read that list: a module there that you would call a solution's inside is a finding about the rule.
- **`arms_on_interface`** is the mean share of its solution's Protocol members that the arms implement, cubed, so the part falls fast: 0.9 reads
  0.73. An offender says which members an arm lacks, and when the arm implements a plain Protocol beside it that has lost its `@solution`
  declaration it says so (restore the declaration, or move the arm to the solution that owns that Protocol). A Protocol that only extends another
  counts the inherited members.
- **"N Protocols signal more than one job"** counts groups of Protocols in a folder, not Protocols: layers that wrap one another (an arm takes the
  Protocol below it as its one constructor need) or that the same arms implement are one group. Several unrelated Protocols implemented by different
  arms are still reported; split the folder at the job, or make the layer that wraps another take it as a constructor need if it truly wraps it.
- **The offenders** are the to-do list, worst first. Each opens with the path or unit to fix (the key a waiver takes) and says what is wrong.
- **What the number cannot tell you**: whether the split fits the domain, whether code was deleted that production needs (only the contract tests,
  run, can say), how many calls a request makes, or whether two solutions with different names do one job in different words. Read the offenders and
  the code for those.

The cases that keep the scorer honest are in `implementations/python/evaluation/components/score_structure_quality/`; run them with
`esoi run score_structure_quality --impl balanced_static`. The expert review arm is paid and never runs without approval.
