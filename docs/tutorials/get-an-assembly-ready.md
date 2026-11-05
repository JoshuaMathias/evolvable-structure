# Assemble a solution and get its environment ready

In this tutorial you declare what two implementations need from their environment, ask `esoi` what is missing, and generate
the files that fix it. It takes about ten minutes, needs only Python 3.9 or later and the `esoi` package, and uses no network.

## 1. Write a tiny package

Make a folder `demo/` with an empty `__init__.py`, and these two files.

`demo/solutions.py` declares one solution, a search:

```python
import typing
from esoi import solution


@solution("search")
class Search(typing.Protocol):
    def find(self, text: str) -> str: ...
```

`demo/arms.py` declares an implementation and, as data next to it, what it needs:

```python
from esoi import implementation
from esoi.runtime.assemble_by_name.environment_needs.declarations import api, env, python


@implementation("search", "openalex")
class OpenAlex:
    REQUIRES = (
        api("OpenAlex", key=env("OPENALEX_API_KEY", secret=True), keyless=True,
            signup_url="https://openalex.org/settings/api", free_tier="free key, higher daily limit", as_of="2026-10"),
        python("requests", "requests>=2.0"),
    )

    def find(self, text):
        return "result for " + text
```

## 2. Ask what the implementation needs

In the folder above `demo/`, run:

```python
from pathlib import Path
from esoi.runtime.assemble_by_name.assemble import Assembler
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig
from esoi.runtime.assemble_by_name.environment_needs.checking import check
from esoi.runtime.assemble_by_name.environment_needs.report import report

parts = Assembler("demo", Path("demo"), modules=("demo.solutions", "demo.arms"))
config = AssemblyConfig(names={"search": "openalex"})
entries = parts.requirements(config)
print(report(entries, check(entries, {})))
```

You see one line per requirement, such as `[met] api OpenAlex, keyless path available` with a remedy line saying that you may
set `OPENALEX_API_KEY` for a free key, or leave it unset. The report lists only the arms this assembly would use, and the
modules they import.

## 3. Generate the files

```
esoi requirements --package demo_assembly --env-template .env.example --install-script install.sh
```

(`demo_assembly` is any importable module that offers an `assembler()` function returning the `Assembler` above.) Open
`.env.example`: the key is blank, with comments giving the signup link, the free tier with its date, and the note that a
key is optional. Open `install.sh`: it holds the `pip install` line for what is missing.

## 4. See the install plan

```
esoi install --package demo_assembly --arm search=openalex
```

It prints the closure, the commands it would run and what only you can do, and changes nothing. Add `--yes` to run it, inside
a virtualenv.

You have declared needs once, next to the code, and generated everything else from them. To declare other kinds of need, see
[the how-to](../how-to/declare-environment-needs.md); to look up a field, see [the reference](../reference/requirements.md).
