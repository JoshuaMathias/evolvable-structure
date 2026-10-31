# The lock: file, API, command line and exit codes

## The file

`esoi.lock.json` (schema `esoi.lock/1`), keys in sorted order:

| Key | Meaning |
|---|---|
| `schema` | `esoi.lock/1` |
| `scope` | The scope of the assembler that wrote it |
| `packages` | The version of each package in the scope chain (`unversioned` when not installed) |
| `update` | Optional policy: `latest` (default) or `safe`. `safe` makes `update` move only solutions that add no unmet requirement |
| `solutions` | Per solution id: `arm`, `scope` (the package whose default chose it), `chain`, `verdict`, `p`, `evidence`, `requirements` |

Each requirement record has `id`, `kind`, `label` and `required`. No value of a variable is stored.

## In the cascade

`AssemblyConfig(lock=path_or_mapping)` adds a layer called `lock` between the consumer's `selection_environ` and the package
defaults. `Assembler.explain` and the `Choice` report it. No `lock` means the latest selections. A locked arm that no longer exists
raises `LockError` (a subclass of `AssemblyError`).

## Functions (`esoi.lock`)

| Function | Does |
|---|---|
| `write(assembler, path, config=None, solutions=(), update_policy=None)` | Records the current selection of each solution and returns the data |
| `read(path_or_mapping)` | The validated lock; raises `LockError` |
| `diff(assembler, source, config=None, solutions=(), environ=None)` | A `Change` per solution whose latest selection differs: `old_arm`, `new_arm`, `verdict`, `p`, `evidence`, `added`, `removed`, `safe` |
| `update(assembler, path, config=None, solutions=(), safe=None, environ=None)` | Moves the lock; returns `Result(moved, blocked, data)`. `safe=None` follows the file's policy |
| `status(assembler, source, config=None, solutions=(), environ=None, package="", file=...)` | `(exit code, plan)` |

`environ` is the environment used to decide whether an added requirement is met (default: the config's `consumer_environ`, else the
process environment). Only names are ever returned.

## Command line

```
esoi lock [--package P | --scope S] [--file esoi.lock.json] [--solution ID ...] [--json]
          [--update [--safe | --latest] | --diff | --status] [--policy latest|safe]
```

Without a mode it writes the lock. `--scope` is the package's top-level name; the package must give `assembler()` or `ASSEMBLER`.

## Exit codes of `--status`

| Exit | Meaning |
|---|---|
| 0 | Up to date |
| 2 | Error |
| 3 | Updates available, all safe |
| 4 | Updates available, at least one blocked by an unmet requirement |

The other modes exit 0 on success and 2 on error.

## The status plan (`esoi.lock.status/1`)

`{schema, lock, state, exit, updates, apply_safe?}` where `state` is `up-to-date`, `safe-updates` or `blocked`. Each update has
`solution`, `old_arm`, `new_arm`, `verdict`, `p`, `evidence`, `safe`, `blocked`, `requirements_added` (each with `status` and
`remedy`), `requirements_removed`, `unmet`, `steps` (each with `order`, `action`, `command`, `detail`, `human`) and `apply`.
Step actions: `install-packages`, `install-binary`, `start-service`, `set-environment`, `resolve`, `apply`, `verify`.
