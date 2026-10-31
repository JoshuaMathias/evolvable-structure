# Declare environment needs beside the arm

An implementation that works on one machine and fails on another usually fails for an unstated reason: a variable that was
set there, a key that was typed once, a package or program that happened to be installed. ESOI's answer is the same as for
every other fact about an implementation: state it next to the implementation, as data, so tools can use it.

## Why next to the arm

The arm's author is the one who knows that it needs `OPENALEX_API_KEY`, that the key is optional, and where to get one. A
hand-written setup document or a `install.sh` kept in a distant folder drifts from the code; a declaration on the arm moves,
changes and is deleted with it. Because it is data, one declaration serves a text report, a check, an `.env` template, an
install script and an install plan, and none of those is written by hand.

These declarations are code, not new fields of the ESOI records. The records say what an implementation is for; the
declaration says what it needs to run.

## The kinds, and what each means

- **env**: a variable, optionally filling a constructor option. The older `ENVIRON` and `ENVIRON_REQUIRED` attributes are read
  as env requirements, so existing arms keep working.
- **api**: an external service, treated specifically because it has an account, a key, official links, a free tier, a rate limit
  and often a keyless path. The author states the free tier and rate limit and dates the statement, since they change.
- **python**: an importable module and the pip requirement that provides it, with the owning package's extra.
- **binary**: a program on PATH. **service**: a running service found by a URL variable. **download**: weights or data fetched
  on first use. **resource**: a note on CPU, memory or time.

A value that is empty or only whitespace counts as unset. No output ever prints a value.

## How assembly reports them: the closure

Declaring is useful only if the report covers exactly what a system uses. `esoi` collects requirements over the **closure** of
an assembly:

1. the arm selected for each solution in use;
2. the arms that fill their needs (a constructor parameter typed with another solution), recursively, as assembly resolves
   them;
3. the modules of the same package that each of those imports, found by reading the source (as a dependency lister does), so a
   requirement declared on a helper module is included.

Each member carries the reason it is in, for example `search-backend:gemini  (needed by know-the-world:web_research)`. An
unselected arm contributes nothing: you install for what you use. Dynamic imports cannot be followed and are noted, as are
modules that cannot be parsed or imported and import cycles (which terminate).

For things code cannot express, a `requirements.txt`, `install.sh` or `install.py` beside an implementation file (named
`<file>.requirements.txt` and so on, or inside the folder of a `__init__.py` or a file named for its folder) is included for
that implementation. This is the shell-level escape hatch; a code declaration is preferred because tools can check and merge
it.

## Conflicts: a ladder, not a stop sign

Two arms may need versions of one package that cannot coexist. The installer then tries, in order, and reports each step:

1. let pip's resolver work on the merged set, with every declaration's own range and the installed versions as constraints;
2. use a declared alternative (another distribution or a wider tested range);
3. use another arm for the least important seat, chosen by the metric ranking, labelled "selected X; using Y here because X
   conflicts with Z", as a circumstance of this environment and never silently;
4. isolate an arm that declares it can run behind a process boundary, in a virtual environment of its own;
5. only then stop, naming the conflicting requirements, who pulls each, and the options for a person.

`esoi requirements --coherence` runs the same logic on the current selection, so a continuous integration job can fail when the
selected implementations stop coexisting. Why a ladder: a conflict is information about the environment, and the structure
should adapt to it by the same selection mechanism that adapts to everything else, while keeping a person informed.
