# Contributing

Only Joshua, or an AI acting on Joshua's own prompt, edits this repository directly. Everyone else is welcome to take part
through issues and pull requests, which Joshua reviews:

- **Issues** for questions, bugs, a template field that reads badly, or an adopter's testimonial.
- **Pull requests** for a change you would like merged. Keep one idea per pull request, say which problem it addresses, and
  expect questions about the metric that shows it helps.

Reading, installing and using `esoi` is open to everyone.

## Ground rules

- The explanation and templates are the main feature. The intent template and the definitions and principles are the
  author's own words in his `SKILL.md`; propose a wording change as an issue, not as an edit to a generated file.
- Adopters appear only in `examples/`.
- No secrets, no real people's emails, no absolute machine paths. Run `esoi hygiene --history` before you push.
- No em dashes, and no underscore-prefixed names in Python.

## Working on the Python implementation

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e "implementations/python[dev]"
python -m pytest implementations/python/tests     # offline, no network
python -m esoi check                              # ESOI applied to this repository
```

A new part of the package joins a component in `esoi/components.csv` and serves a solution in
`esoi/solutions.csv`; a new rule needs a mutation case in the `check_the_structure` evaluation component.
