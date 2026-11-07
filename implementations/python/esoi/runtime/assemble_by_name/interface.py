"""The interface of AssemblingByName: a Protocol declared with ``@solution``, and the arms this solution ships beside it. Importing this module runs nothing."""
from typing import List, Protocol, runtime_checkable

from esoi.runtime.implementation_selection.declare import implementation, solution
from esoi.runtime.assemble_by_name.entry import own_runner  # noqa: F401  (re-exported: the command line calls this unit through its interface)
from esoi.runtime.assemble_by_name import assemble
from esoi.runtime.assemble_by_name.assemble import Assembler, package_assembler  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.runtime.assemble_by_name.assembly_config import AssemblyConfig  # noqa: F401  (re-exported: other units call this unit through its interface)
from esoi.runtime.assemble_by_name.intent_map import snapshot
from esoi.runtime.assemble_by_name.hierarchy import OVERRIDES_FILE, UNCONFIRMED, check_reasons, parent_defaults, read_overrides
from esoi.runtime.assemble_by_name.lock_file import CACHE as lock_file_CACHE, SCHEMA as lock_file_SCHEMA, locked_arm as lock_file_locked_arm, read as lock_file_read
from esoi.runtime.assemble_by_name.environment_needs.closure import Member, members_pairs
from esoi.runtime.assemble_by_name.environment_needs.report import EXIT_ERROR, EXIT_MET, EXIT_UNMET, as_json as requirements_json, report as requirements_text
from esoi.runtime.assemble_by_name.installation.assembly_plan import assembly_plan
from esoi.runtime.assemble_by_name.installation.plan_report import plan_json, plan_text
from esoi.runtime.assemble_by_name.installation.resolvers import venv_resolver
from esoi.runtime.assemble_by_name.environment_needs.generated_files import install_script, write_env_file
from esoi.runtime.assemble_by_name.environment_needs.checking import MET, check
from esoi.runtime.assemble_by_name.environment_needs.declarations import Entry, Network, declared, gather, identity
from esoi.runtime.assemble_by_name.installation.resolution_ladder import make_plan
from esoi.runtime.assemble_by_name.installation.execution import execute, package_roots

__all__ = ["Assembler", "package_assembler", "EXIT_ERROR", "EXIT_MET", "EXIT_UNMET", "requirements_json", "requirements_text", "AssemblingByName", "AssemblyConfig", "Entry", "MET", "Member", "Network", "OVERRIDES_FILE", "UNCONFIRMED", "assemble", "assembly_plan", "check", "check_reasons", "declared", "execute", "gather", "identity", "install_script", "lock_file_CACHE", "lock_file_SCHEMA", "lock_file_locked_arm", "lock_file_read", "make_plan", "members_pairs", "own_runner", "package_roots", "parent_defaults", "plan_json", "plan_text", "read_overrides", "snapshot", "venv_resolver", "write_env_file"]


@solution("assemble-by-name", kind="event", entry="names", example="structure-check")
@runtime_checkable
class AssemblingByName(Protocol):
    """The implementation names a solution of esoi can be built from."""

    def names(self, solution_id: str) -> List[str]: ...


@implementation("assemble-by-name", "assembler")
class AssemblerByName:
    """An Assembler over esoi's own solutions."""

    def names(self, solution_id: str) -> List[str]:
        from esoi.runtime.assemble_by_name.entry import own_runner
        return own_runner().assembler.names(solution_id)
