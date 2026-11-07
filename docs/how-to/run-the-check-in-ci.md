# Run the check in continuous integration (an example)

Use this if you want your own repository's tests, structure check and hygiene scan to run on a hosting service's pull requests and pushes.
It is an example to copy, not something every project needs: ESOI runs the same commands by hand (`esoi check`, `esoi hygiene`), and this
repository runs no workflow of its own, so editing a README starts no process.

## The example (GitHub Actions)

Save it as `.github/workflows/check.yml` in your repository and change the install line to match where your package lives.

```yaml
name: check

on:
  pull_request:
  push:
    branches: [main]

jobs:
  offline-metrics:
    # No metric runs here: a metric runs on a decision (esoi/metric-run-policy.md), and a stale result only informs.
    # This job runs the tests, the structure check (a structure problem fails it) and the hygiene scan; arms that call a model run only on a decision.
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: pip install -e "implementations/python[dev]"
      - run: python -m pytest implementations/python/tests
      # A structure problem fails the job; advisory findings are printed and exit 0.
      - run: esoi check
      - run: esoi hygiene
      # A stale recorded result only informs (the measured code changed since its commit): warn, never fail.
      - if: github.ref == 'refs/heads/main'
        run: esoi check --strict || echo "::warning::esoi check --strict reported stale results or structure findings, see the log above"
```

## What it does

- It runs your tests, then `esoi check` (a structure problem fails the job; advisory findings are printed and exit 0), then `esoi hygiene`.
- It runs no metric. A metric runs on a decision ([when metrics are run](../explanation/when-metrics-are-run.md)), and a stale result only informs.
- `fetch-depth: 0` gives `esoi hygiene --history` the full history it needs.
