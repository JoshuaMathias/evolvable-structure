# Adopters

Short notes from repositories that applied ESOI. They are examples and testimonials, not part of the method, and nothing in
this repository depends on them.

## quest-ai-runner

An open-source library that runs AI tasks and chat for a product. It was the first repository to apply ESOI end to end, and
the tools in `implementations/python/` were extracted from what it had built: a registry of components and solutions, an
evaluation component per solution with recorded runs, a leaderboard that selects implementations, and a check that runs in
its tests. Its detailed records link up to an overall network it wrote separately. It keeps a small rule of its own (for
environment variables) as a plugin, which is the intended use of the plugin interface.
It also wrote the first cases for measuring whether an AI agent acts by the principles, with a model judge scored against
labelled replies; the generic version of both is in [esoi-for-ai.md](../docs/explanation/esoi-for-ai.md).

## quest-backend

A service built on that library. It lists each place it uses the library as a row of an integration registry and checks
the rows, its recorded results and its version pin with the consumer check (`esoi consumer check`), so drift in how it uses
the library fails a normal test run.

## Adding yours

Open an issue with a paragraph or two: what you applied it to, what the overall network said, and what changed once a metric
chose between alternatives. Failures are as useful as successes.
