# Adopters

Short notes from repositories that applied ESOI. They are examples and testimonials, not part of the method, and nothing in
this repository depends on them.

## quest-ai-runner

An open-source library that runs AI tasks and chat for a product. It was the first repository to apply ESOI end to end, and
the tools in `implementations/python/` were extracted from what it had built: a registry of components and solutions, an
evaluation component per solution with recorded runs, a leaderboard that selects implementations, and a check that runs in
its tests. It uses the older two-level layout (an overall network plus detailed records), which still loads and can be migrated to intents. It keeps a small rule of its own (for
environment variables) as a plugin, which is the intended use of the plugin interface.
It also wrote the first cases for measuring whether an AI agent acts by the principles, with a model judge scored against
labelled replies; the generic version of both is in [esoi-for-ai.md](../docs/explanation/esoi-for-ai.md).

## quest-backend

A service built on that library. It lists each place it uses the library as a row of an integration registry and checks
the rows, its recorded results and its version pin with the consumer check (`esoi consumer check`), so drift in how it uses
the library fails a normal test run.

## ai-hub-of-hubs-structure

A repository of AI-intelligence hubs (model call, web search, card store, risk watching) and the code that wires them into one
program. It had written, for its own use, a name validator, a loader that refused modules outside its package, a registry
lookup by name, a reader of constructor types, a builder that ordered parts by their needs, and a check that the recorded
needs matched the code. None of that mentions AI, so it moved into the library as `esoi.assemble`
([guide](../docs/guides/assemble-by-name.md)). The repository now constructs one `Assembler` for its package and uses
`AssemblyConfig` and `AssemblyError` directly, with no aliases of its own. It keeps what is about its domain: its solutions as
Protocol classes, its arms, its configuration, the rule that picks a model tier, the card store, the risk watcher and the
scoring of its registry. The one piece that looked general and stayed is the scan that finds vendor names in a consumer's core
code: it takes the application's vendor terms, so the question it answers is the application's.

## Adding yours

Open an issue with a paragraph or two: what you applied it to, what the intent's vision statement and problems said, and what changed once a metric
chose between alternatives. Failures are as useful as successes.
