"""The interface of SkillDistributing: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import Dict, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.structure.intent_registry.registry import load_project


@solution("skill-distribution", kind="evaluate", entry="copies", example=".")
@runtime_checkable
class SkillDistributing(Protocol):
    """The committed copies of the author's skill: how many files each holds."""

    def copies(self, project: str) -> Dict[str, int]: ...


@implementation("skill-distribution", "generated-public-copy")
class GeneratedPublicCopy:
    """Copies generated from the private skill folder and checked for leaks."""

    def copies(self, project: str) -> Dict[str, int]:
        from esoi.understanding.the_standard.skill_distribution import skill
        cfg, found = load_project(project)
        return {folder.relative_to(cfg.root).as_posix(): len(skill.read_copy(folder)) for folder in skill.copy_folders(cfg, skill.settings_from(cfg))}
