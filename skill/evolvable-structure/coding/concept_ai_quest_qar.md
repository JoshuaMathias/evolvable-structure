# evolvable-structure coding examples: Concept AI, Quest and quest-ai-runner

Part of `../coding.md`. Spiritual Data's own systems. Load when working in those codebases, or on domain engines, keeping a product generic, or deployments as config. These are how one project met an ideal, not rules for every
project: carry over the purpose, and copy the mechanism only where the codebase already uses it.
Evidence pointers read `file > heading`, with files in `../sources/`.

**10. Concept AI: domain engines take the domain as a parameter, and weights are measured.**
*Purpose:* one engine for every domain, with values that come from measurement (patterns 1, 7 and 9).
Domains are YAML over one action and decision engine, prompts live in one central module, and a
source's weight is its measured reliability, so a new source joins with no weight until it earns one.
A capability a second domain needs moves into the framework. Joshua, 2026-10-17: "every domain in
shared-domains (other than perspctives I guesss) should be a solution", and "esoi should determine what
goes in shared-domains vs conceptai". So each non-perspective domain has a solution record in
`shared-domains/structure/` linked to an area of `conceptai/structure/overall/`; perspective domains are
data that the build-perspectives area produces. Placement follows where "best" is defined: a port, its
selection entry and generic implementations go in conceptai; a domain's definition, data, prompts and
cases stay in shared-domains, and a domain-specific implementation registers into conceptai's selector.

**11. Quest: generic in the product, specific outside it.** *Purpose:* a core free of one party's
logic (pattern 6). Quest carries no Spiritual Data-only config, setting, env var, error message or code path; Spiritual Data's
tools connect through the public API or webhook. New Quest settings arrive as one optional field
defaulting to the old behaviour.

**16. quest-ai-runner: a deployment is a config file, reached through one front door.** *Purpose:* a
new deployment is configuration, not a program, and a library has one entry point (patterns 1 and 6). A
lane is one TOML file: a capability is on when its table is present, env layers resolve in a fixed,
truthy-checked order, and scripts reach the Quest API through `load_client(<config path>)` rather than
their own client module. When three consumers hand-rolled the same driver, the fix was one library
entry point.

## Known weaknesses

QAR's playbook and code disagree on the default model ladder, and a tier fallback ran silently for weeks. Lesson: a fallback says so in the log.
