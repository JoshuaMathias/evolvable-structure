# Scope the role of a solution

A solution is a **role**: what a part of the system is responsible for, what it hands to others, and what it is explicitly not
responsible for. Defining solutions is specialization and delegation of responsibility. When roles are not scoped, the hierarchy fills
with overlapping parts (an "Acting" that holds file edits and coding agents; a "Hands" that only re-justifies tool calling a sibling
already covers). This page is the checklist, written after Joshua found those nuances had to be asked for one at a time.

## The fields that carry the role

| Field | Says | Notes |
|---|---|---|
| `purpose` | what the solution is responsible for | one sentence, a verb, who it serves |
| `approach` | how it does that, true of every implementation | |
| `out_of_scope` | what it is explicitly **not** responsible for | the exclusions that are not obvious |
| `delegates_to` | **who owns** what it excludes or hands on: the ids of the sibling solutions (`none` says nothing is delegated and no sibling owns it) | a column of `solutions.csv`; `out_of_scope` names the thing, `delegates_to` names the owner |
| `change_driver` | for a **container-level** part: what kind of change moves its metric | one of: outside systems; the system's own data model or code; ML task accuracy; alignment with humans or policies |

`out_of_scope` stays in the template's words (what use cases it avoids). Because the template says not to name other solutions there,
the owner goes in `delegates_to`, not in the sentence.

## Scope a role, in order

1. **Say the role in a sentence** (`purpose`) and what it excludes (`out_of_scope`). A solution with siblings and nothing excluded has
   not been scoped against them.
2. **Find the owner of every exclusion** and write it in `delegates_to`. If no sibling owns it, that is a gap in the hierarchy: add the
   solution, or say `none` and why.
3. **Compare with each sibling.** Do the two purposes overlap? If so, merge them, split the job so each owns one role, or let one
   delegate to the other. Ask of each solution: is it justified only by a capability a sibling or the world already provides? Then it
   is not a solution.
4. **Read the implementation list.** A solution holds alternatives that do the SAME job at the same level of specificity
   ([why](../explanation/a-solution-holds-alternatives-of-one-job.md)). Arms with different purposes mean the solution is mis-defined:
   split by purpose.
5. **For a container** (a solution one of whose implementations is a sub-intent), name the `change_driver`: what makes its metric move.
   Parts with different change drivers are different containers.

## What esoi checks

All advisory, in `esoi check --findings`, never a failure; each is a prompt for the person who owns the specification.

- **S48** a solution with siblings that states no exclusions; exclusions with no owner (once the repository has a `delegates_to`
  column, a solution whose `out_of_scope` names no sibling and whose `delegates_to` is empty); a `delegates_to` that names no solution;
  two siblings whose purpose and description share most of their content words (merge, split or delegate); and a container with no
  `change_driver`. A repository with no `delegates_to` column gets one line per intent saying to add it. Waive as the solution id, or
  `a+b` for a pair.
- **S49** a review prompt for a solution with three or more implementations whose descriptions share little: read the list for one
  purpose and one specificity. It is a prompt, not a verdict: alternatives that look different may still do one job.

The word-overlap tests are heuristics. They find candidates to read, not roles that are wrong.
