# Install only what your solutions need

Use this to install the dependencies of the solutions you actually use, and nothing else. It assumes the arms declare their needs
(see [declare what an implementation needs](declare-environment-needs.md)).

## Plan, then apply

```
esoi install --package mypackage --solution know-the-world
```

This prints the closure (the selected arm, the arms that fill its needs, the package modules each imports, each with the
reason it is in), the commands it would run, and what only you can do: install a program, set a key. It changes nothing. Without
`--solution` it plans for what a default assembly would use. When you are happy with the plan, run it in a virtualenv:

```
esoi install --package mypackage --solution know-the-world --yes
```

To plan for a different arm, add `--arm solution=name`; for every arm of the solutions, `--all-arms`.

## When requirements conflict

The plan says so and shows the resolution ladder: the resolver with installed versions kept, a declared alternative, another arm
for the least important seat, ranked by the scope's own leaderboard (labelled, never silent), an isolated environment for an arm that allows it, and finally the exact
conflict with the options for you. See [the explanation](../explanation/environment-needs.md).

## Re-run after a failure

A failed step is reported with the end of its output and installs nothing further. Fix the cause and run the same command:
what is now satisfied is skipped.

## Check coherence in CI

```
esoi requirements --package mypackage --coherence
```

exits 1 if the selected implementations' requirements cannot coexist as declared.
