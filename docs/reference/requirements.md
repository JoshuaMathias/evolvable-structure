# Requirements: kinds, fields and commands

Declarations live in `esoi.requirements`. An arm attaches them with a `REQUIRES` tuple (on the class or function, or at module
level in a helper module). `ENVIRON = {option: variable or (variables)}` and `ENVIRON_REQUIRED` keep working and are read as
env requirements. Every constructor takes keyword arguments after the first.

## Kinds

| Constructor | Fields | Meaning |
|---|---|---|
| `env(name, option=None, required=True, secret=False, also=(), group="", note="")` | `also`: alternative names, any one suffices; `group`: variables of which any one is enough | A variable; `option` is the constructor option it fills. Empty or whitespace counts as unset. |
| `api(service, key=None, keyless=False, signup_url, docs_url, pricing_url, free_tier, rate_limit, as_of, probe_url, required=True)` | `key` is an `env(...)`; `as_of` dates the free tier and rate limit | An external API. With `keyless=True` it is met without the key, and the remedy names the optional key. |
| `python(module, distribution, extra=None, required=True, alternatives=())` | `distribution` may carry a range and a marker; `alternatives` are other requirement strings providing the module | An importable module and the pip requirement for it. |
| `binary(name, install_hint="", version_args=None, required=True)` | `version_args` is run only with a probe | An executable on PATH; reports "found but not executable". |
| `service(name, url_env, default_url=None, health_path=None, required=True)` | | A running service found by a URL variable. Unknown while only the default is assumed. |
| `network(host="", required=True)` | `host` names where, for the reader | The arm reaches the network. Met normally; unmet while `ESOI_OFFLINE=1`, for `esoi.entry` and for `esoi run` alike (the run prints `pending-network`, records nothing and exits 0), with the remedy "needs network access; not attempted offline", so the arm is pending (outcome `pending-network`) and is never built. |
| `download(name, size_mb=0, cache_hint="")` | | Fetched on first use. Checks free disk space against `size_mb`; informational unless it will not fit. |
| `resource(note)` | | A CPU, GPU, memory or time note. Informational. |
| `isolatable(boundary)` | `subprocess`, `cli` or `mcp` | The arm can run out of process, so its python requirements may be installed in an environment of its own. |

Per-implementation files, the second declaration form: `<file>.requirements.txt`, `<file>.install.sh`, `<file>.install.py`
beside an implementation file, or `requirements.txt`, `install.sh`, `install.py` in the folder of an `__init__.py` or of a file
named for its folder. They run in the order install.sh, requirements.txt, install.py.

## Functions

- `declared(target)`: the requirements of an arm or module.
- `check(requirements, environ, probe=False, offline=False)`: a `Check(requirement, status, remedy)` per item, status `met`,
  `unmet` or `unknown`. No network unless `probe=True`; `offline=True` disables every probe.
- `Assembler.closure(config, provided, solutions=(), every_arm=False)`: the members with the reason each is in.
- `Assembler.requirements(config, provided, every_arm=False, solutions=())`: the deduplicated requirements of the closure.
- `Assembly.requirements`: the same for the arms an assembly built.
- `pending_needs` and `assemble_defaults` treat an unmet required env, api, python, binary or network as pending with its remedy line.
- `env_template`, `install_script`, `write_env_file`, `report`, `as_json`: the generated outputs.
- `esoi.installer.make_plan`, `assembly_plan`, `execute`: the install plan, the resolution ladder and the guarded runner.

## Exit codes and JSON

`esoi requirements --check` and `esoi install` exit 0 when everything is met or done, 1 when something is unmet or still to do
(for `--coherence`, when the selected arms conflict), and 2 on an error. JSON carries `"schema": "esoi.requirements/1"` (or
`"esoi.install/1"`); fields are only ever added within a schema version. No output contains a variable's value.

## `esoi requirements`

`esoi requirements [--package P | --scope S] [--solution ID ...] [--arm SOLUTION=NAME ...] [--all-arms] [--check] [--probe] [--offline] [--coherence [--online]] [--json] [--env-template FILE] [--env-file FILE] [--install-script FILE]`

`--package` imports P and uses its `assembler()` (or `ASSEMBLER`), reporting the closure of the default assembly. `--scope`
reports every declared arm of a registry scope. `--env-template` writes a template (a name ending `.example`, `.template`,
`.sample` or `.dist` is regenerated whole). `--env-file` adds missing variables, commented, to any other file, never changing
what is there, mode 600, refusing a git-tracked file. `--coherence` checks that the selected implementations resolve
together; `--online` asks pip for a dry run in a temporary virtualenv.

Sample:

```
[met] api OpenAlex, keyless path available, free tier: free key, higher limit (as of 2026-10)  <- search:openalex
    remedy: set OPENALEX_API_KEY (free key: https://example.org/key), or leave it unset to use the keyless path
[unmet] python module requests from requests>=2.0  <- search:openalex
    remedy: pip install 'requests>=2.0' (use a virtualenv)
```

## `esoi install`

`esoi install [--package P | --scope S] [--solution ID ...] [--assembly] [--arm SOLUTION=NAME ...] [--all-arms] [--project DIR] [--yes] [--json]`

Computes the closure, applies the resolution ladder, prints the plan, and changes nothing without `--yes`. With `--yes` it
uses `sys.executable -m pip` in the current environment only, refuses an externally managed one (PEP 668), takes a per
environment lock, makes one pip call for the whole set (timeout 15 minutes), runs `pip check`, then runs per-implementation
files only from inside the package directory (working directory: the file's folder; `sh` for `.sh`, the current interpreter for
`.py`; 10 minute timeout) and stops at the first failure with the step and the masked tail of its output. Isolated arms go under
`<project>/.esoi/venvs/`.

`Assembler.metric_order(solution_id, selected)` returns `(arm names best first, lead, note)` from the scope's records and results (`lead` 1.0 when the selected arm's lead over its runner-up is significant by `leaderboard.decisions`, 0.0 otherwise, None without results). `assembly_plan(rank=..., lead=...)` hooks override it.
