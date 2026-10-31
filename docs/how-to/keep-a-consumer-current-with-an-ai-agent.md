# Keep a consumer current with an AI agent

Use this when an AI agent maintains a program that uses an ESOI package with a lock (see
[Pin selections for production and update on your schedule](pin-selections-for-production.md)). The agent notices that a newer
selection is available, resolves what it needs, applies it and verifies, and asks a person only for what only a person can give,
such as a key.

## 1. Run the status on a schedule

```bash
esoi lock --package mylib --status --json
```

The exit code is stable, so a scheduler can branch on it without reading the output:

| Exit | Meaning |
|---|---|
| 0 | Up to date: the latest selections equal the locked ones |
| 3 | Updates are available and every one is safe (adds no unmet requirement) |
| 4 | Updates are available and at least one is blocked by an unmet requirement |
| 2 | Error: no lock, an unreadable lock, a package without an assembler |

## 2. Read the plan

The JSON has `schema` `esoi.lock.status/1` (fields are only ever added within a version), a `state`, and one entry in `updates`
per solution that would change: `old_arm`, `new_arm`, `verdict`, `p`, `evidence`, the `requirements_added` and
`requirements_removed`, `safe`, `blocked`, the `unmet` requirements, the `steps` in order and `apply`, the one command that applies
that update. A top-level `apply_safe` applies every safe update at once.

## 3. Apply what is safe

```bash
esoi lock --package mylib --update --safe
```

## 4. Resolve each blocked update

Take the steps of a blocked update in order. An action is one of:

- `install-packages`: run its `command` (an `esoi install ... --yes`).
- `install-binary` and `start-service`: do what the `detail` says; it is the requirement's own remedy.
- `set-environment`: set the named variables. If the step has `"human": true` it is a key or a secret: do not invent one. Ask a
  person for it, using the signup link in the `detail`, and never write a key into a file you commit.
- `apply`: run the step's `command`, `esoi lock --update --solution <id>`, once the earlier steps are done.
- `verify`: see below.

If a step needs a person and none is available, leave the solution locked. The lock stays valid and `--status` keeps reporting it.

## 5. Verify

```bash
esoi requirements --check --package mylib --solution store
```

Exit 0 means every requirement of the new arm is met. Then run the consumer's own tests, and commit `esoi.lock.json` with the
evidence line of each change in the message. If the tests fail, restore the lock from version control: nothing else changed.

## A loop for the agent

1. `esoi lock --status --json`. Exit 0: stop.
2. Exit 3 or 4: `esoi lock --update --safe`.
3. For each remaining blocked update: resolve its steps, run its `apply` command, verify.
4. Run the tests and commit, or restore and report what blocked.
