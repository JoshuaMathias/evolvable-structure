# Skill Distribution

**Purpose:** Publish an author's skill from the private folder where it is maintained as a complete public folder that people install without anything else.

Breadcrumb: [Top](../../../../../../esoi/README.md) > [How People and Agents Come to Apply ESOI](../../README.md) > [The Standard](../README.md) > Skill Distribution

Part of [The Standard](../README.md)

## Skill Distribution (`skill-distribution`)

- Out of scope: Deciding what the skill says, and hosting the published copy.
- Entry call: `esoi.run("skill-distribution", '.')`
- Selected implementation: Generated public copy (`generated-public-copy`)
- Metric: Skill copy agreement and leaks
- Implemented by: [`.claude-plugin/marketplace.json`](../../../../../../.claude-plugin/marketplace.json), [`implementations/python/esoi/data/skill/evolvable-structure/INDEX.md`](../../../data/skill/evolvable-structure/INDEX.md), [`implementations/python/esoi/data/skill/evolvable-structure/SKILL.md`](../../../data/skill/evolvable-structure/SKILL.md), [`implementations/python/esoi/data/skill/evolvable-structure/coding.md`](../../../data/skill/evolvable-structure/coding.md), [`implementations/python/esoi/data/skill/evolvable-structure/coding/components.md`](../../../data/skill/evolvable-structure/coding/components.md), [`implementations/python/esoi/data/skill/evolvable-structure/coding/concept_ai_quest_qar.md`](../../../data/skill/evolvable-structure/coding/concept_ai_quest_qar.md), [`implementations/python/esoi/data/skill/evolvable-structure/coding/pipelines_and_experiments.md`](../../../data/skill/evolvable-structure/coding/pipelines_and_experiments.md), [`implementations/python/esoi/data/skill/evolvable-structure/coding/registry_and_templates.md`](../../../data/skill/evolvable-structure/coding/registry_and_templates.md) and 62 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Generated public copy | `skill-distribution:generated-public-copy` | A command copies the listed files from the private folder, removes marked private passages, applies the few listed substitutions, and a second command checks freshness and leaks. | [`implementations/python/esoi/understanding/the_standard/skill_distribution/interface.py`](interface.py) | selected |
| Hand-copied folder | `skill-distribution:hand-copied-folder` | Someone copies the public files by hand and edits out what is private. | no code yet |  |
| Publish the private folder | `skill-distribution:publish-the-private-folder` | Publish the whole folder as it is. | no code yet |  |

## Metrics

- Skill copy agreement and leaks (`metric-skill-copy-agreement`): leader `live_skill`, 26 of 26 cases

## Problems

- Skill cannot be reached safely (`prob-skill-cannot-be-reached-safely`): A person who wants to use the author's skill cannot get it in a form that is both complete and safe to publish.

## Ideals

- Installable skill (`ideal-installable-skill`): A stranger gets the author's current skill, complete and public-safe, in one step, while the author keeps one source of truth.

## Where to go next

- Up: [implementations/python/esoi/understanding/the_standard](../README.md)
- Intent: [How People and Agents Come to Apply ESOI](../../README.md)
- Repository: [top README](../../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
