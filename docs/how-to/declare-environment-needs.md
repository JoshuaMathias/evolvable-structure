# Declare what an implementation needs from its environment

Use this when an implementation needs variables, API keys, packages, programs or services, and you want users of the solution
to get them set up automatically. For a first walk-through see [the tutorial](../tutorials/get-an-assembly-ready.md).

## Declare the needs

Add a `REQUIRES` tuple to the class (or function) that implements the solution:

```python
from esoi.runtime.assemble_by_name.environment_needs.declarations import api, binary, download, env, python, service

class WebResearch:
    REQUIRES = (
        api("Gemini", key=env("GEMINI_API_KEY", option="api_key", secret=True, also=("GOOGLE_API_KEY",)),
            signup_url="https://example.org/key", pricing_url="https://example.org/pricing",
            free_tier="limited free requests", rate_limit="per minute, see the docs", as_of="2026-10"),
        python("hubofhubs_web", "hubofhubs", extra="web"),
        binary("ffmpeg", "install ffmpeg with your package manager", version_args=("-version",)),
        service("Qdrant", "QDRANT_URL", default_url="http://localhost:6333", health_path="/healthz"),
        download("embedding model", size_mb=130, cache_hint="~/.cache/huggingface"),
    )
```

- Put `keyless=True` on an `api` that works without its key.
- `option="api_key"` fills that constructor option from the variable, so `ENVIRON` is not needed. An existing `ENVIRON` /
  `ENVIRON_REQUIRED` pair still works and is read as env requirements.
- A requirement all the arms of a helper module share can be declared once as a module-level `REQUIRES` in that module; any arm
  that imports it includes it.
- A version range goes in the distribution string: `python("requests", "requests>=2.31; python_version>='3.9'")`.

## Check, and generate the files

```
esoi requirements --package mypackage --check
esoi requirements --package mypackage --env-template .env.example --install-script install.sh
esoi requirements --package mypackage --env-file .env
```

`--env-file` adds the variables missing from your `.env`, commented out; it never changes a line you wrote, creates the file
with mode 600 and refuses a file git tracks. The generated `.env.example` contains no values.

## Install and keep coherent

To install only what your solutions need, see [the how-to](install-only-what-you-need.md).

### Keep the selected implementations coherent

```
esoi requirements --package mypackage --coherence
```

Exit code 1 means the selected implementations' requirements cannot coexist as declared; the output shows the ladder's
proposed fix. Add `--online` to let pip check in a temporary virtualenv.

## Troubleshooting

- **"externally managed"**: create and activate a virtualenv (`python -m venv .venv && . .venv/bin/activate`), then run again.
  `--break-system-packages` is never used.
- **"another esoi install is running"**: wait for it; the lock is per environment.
- **A step failed**: the report names the step and shows the last lines of output with secret values masked. Fix the cause and
  run the same command again: what is now satisfied is skipped.
- **"pip check found conflicts"**: the installed set has inconsistent requirements. Widen one declared range or deselect an arm;
  `esoi install` shows the options.
- **A script was refused**: install files must lie inside the package directory once links are resolved.
- **"no sh on this system"**: on Windows, use WSL or Git Bash, or move the steps into a `python(...)` declaration.
- **Version "not verified"**: `packaging` is not installed, so pip decides. Install it for exact checks.
- **A binary is "not executable"**: `chmod +x` it, or reinstall.
- **A service shows unknown**: it is assumed at its default address; set its URL variable, or pass `--probe` (never with
  `--offline`).
- **Exit codes**: 0 all met, 1 something unmet or to do, 2 an error such as an unknown package.
