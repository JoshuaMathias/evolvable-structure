# Pin selections for production and update on your schedule

Use this when your program depends on an ESOI package and you want to decide when it moves to a newer selected implementation. By
default you do not need to: ESOI selects the best-scoring implementation, and an assembly takes the latest selection right away.
That default is right for a new solution, a prototype, and anything without end users yet. This page is for the other case.

## Is pip pinning already enough?

An installed release carries its code and its selections together: the package's `esoi_selection.json` is part of the release, so
`pip install mylib==1.4.0` gives you the arms of 1.4.0 and the selection 1.4.0 shipped. If you pin the version and upgrade on
purpose, you already update on your schedule, and you do not need a lock.

A lock helps in two situations that pinning cannot express:

- **You track a git branch or a moving source** (a checkout, `pip install git+...@main`). The code and the selections move at every
  commit, and there is no release number to hold.
- **You want code fixes without selection changes.** You upgrade the package for a bug fix, but the same release also switched a
  solution to a different arm, and you want that switch to wait until you have looked at it.

## Write the lock

```bash
esoi lock --package mylib                  # writes esoi.lock.json
esoi lock --package mylib --policy safe    # also records update = "safe" (see below)
```

Commit `esoi.lock.json`. For each solution it records the selected arm, the scope that chose it (and the parent chain, when the
package builds on another), the verdict and p-value of the evidence at that time, and the requirements of the arm's closure
(variables, API keys, python packages, binaries, services). It also records the version of each package in the chain.

Tell your assembly to use it:

```python
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig

system = parts.assemble(AssemblyConfig(lock="esoi.lock.json"))
system.explain("store")        # the layer shown for each locked solution is "lock"
```

The lock sits between your own `selections` and the package defaults, so a selection you wrote yourself still wins. With no `lock`
you follow the latest selections, as before. A locked arm that the package no longer lists raises `LockError` that names the
solution, the arm and the remedy.

## See what a newer release would change

```bash
esoi lock --package mylib --diff
```

For each solution whose latest selection differs from the lock it shows the old arm, the new arm, the verdict and p, and the
requirement changes between the two closures: variables and API keys, python packages and extras, binaries, services and
downloads that the new arm adds or no longer needs. Each added requirement says whether the current environment already meets it.
No variable's value is printed.

## Move the lock

```bash
esoi lock --package mylib --update                   # move everything, printing each change with its evidence
esoi lock --package mylib --update --safe            # move only what adds no unmet requirement
esoi lock --package mylib --update --solution store  # one solution
```

`--safe` leaves a solution locked when its new arm needs something the environment lacks, and prints the exact remedy: the
variables to set with their signup links, the `esoi install` command, the binary to install. A lock file with
`"update": "safe"` makes `--update` behave that way unless you pass `--latest`. After a move, run your tests, then commit the lock.

From code the same operations are functions:

```python
from esoi import lock

lock.write(parts, "esoi.lock.json")
changes = lock.diff(parts, "esoi.lock.json")
result = lock.update(parts, "esoi.lock.json", safe=True)    # result.moved, result.blocked
```

An AI agent can run this loop for you: see [Keep a consumer current with an AI agent](keep-a-consumer-current-with-an-ai-agent.md).
The reference for the file, the functions and the exit codes is [The lock](../reference/lock.md).

## Choosing the default

For ESOI and for packages that use it, the default stays "use better solutions right away": no lock, latest selections. Lock only
what has production end users, and keep the choice per consumer, since the producer cannot know who depends on it. The metric's
side of this is in [Choosing by metric](../explanation/choosing-by-metric.md): a solution can also require a significant lead
before the package itself switches its selection.
