# evolvable-structure coding examples: engines with data-defined domains, a generic product core, deployments as config

Part of `../coding.md`. Three techniques, each shown by one of the author's own systems (Concept AI, Quest, quest-ai-runner). Load
when a second case differs only in data, when one party's logic is creeping into a shared core, or when several deployments of one
program differ. These are how one project met an ideal, not rules for every project: carry over the purpose, and copy the mechanism
only where the codebase already uses it. Project-specific working notes (placement rules, repository quirks) live in the local ESOI
index, not here. Evidence pointers read `file > heading`, with files in `../sources/`.

**10. Domains as data over one engine, with measured weights (Concept AI).** *Technique:* one engine for every domain, with values
that come from measurement (patterns 1, 7 and 9). *When relevant:* each new case would otherwise bring new code, or hand-set
importances that nobody measured. Domains are YAML over one action and decision engine, prompts live in one central module, and a
source's weight is its measured reliability, so a new source joins with no weight until it earns one. A capability a second domain
needs moves into the framework. Where a part lives follows where "best" is defined: a port, its selection entry and generic
implementations belong with the engine; a domain's definition, data, prompts and cases belong with the domain. When a domain-specific
implementation is needed it registers into the engine's selector rather than editing the engine. Data that another process produces
(for example generated perspectives) is data, not a solution.

**11. Keeping a product core generic, with the specific connected from outside (Quest).** *Technique:* a core free of one party's
logic (pattern 6). *When relevant:* the product's owner wants its own workflows in the product. For example, Quest carries no config,
setting, env var, error message or code path that only the author's own organization needs; that organization's tools connect through
the public API or a webhook. New settings arrive as one optional field defaulting to the old behaviour. The test is whether the
screen, setting or error would make sense to a stranger's team.

**16. A deployment is a config file, reached through one front door (quest-ai-runner).** *Technique:* a new deployment is
configuration, not a program, and a library has one entry point (patterns 1 and 6). *When relevant:* several deployments or consumers
of one library each carry their own wiring. A lane is one TOML file: a capability is on when its table is present, env layers resolve
in a fixed, truthy-checked order, and scripts reach the product's API through `load_client(<config path>)` rather than their own
client module. When three consumers hand-rolled the same driver, the fix was one library entry point.

## Known weaknesses

In quest-ai-runner the playbook and code disagreed on the default model ladder, and a tier fallback ran silently for weeks. Lesson: a fallback says so in the log.
