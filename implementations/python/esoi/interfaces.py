"""esoi's own solutions as interfaces, so ``esoi.run(id, input)`` reaches them like any project's: the checks a person applies
to a project, and the selection that decides which implementation serves a call. Each solution is one Protocol with its kind, entry
and an example that answers offline and read-only; each implementation here calls the function that does the work in its own module.
Importing this module runs nothing."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from .runtime import implementation, solution


@solution("structure-check", kind="evaluate", entry="check", example=".")
@runtime_checkable
class StructureChecking(Protocol):
    """The problems of a project's records and code against the rules, one line each (empty when it passes)."""

    def check(self, project: str) -> List[str]: ...


@solution("apply-esoi", kind="evaluate", entry="review", example=".")
@runtime_checkable
class ApplyingEsoi(Protocol):
    """How far a project applies ESOI: its structure problems by rule and its solution coherence, in one report."""

    def review(self, project: str) -> Dict[str, Any]: ...


@solution("implementation-selection", kind="event", entry="choose", example="structure-check")
@runtime_checkable
class ImplementationSelecting(Protocol):
    """The implementation that serves a solution of the calling project now, and the layer of the cascade that chose it."""

    def choose(self, solution_id: str) -> Any: ...


@implementation("structure-check", "rule-script")
class RuleScript:
    """Every built-in and plugin rule over the project's records and files (``esoi check``)."""

    def check(self, project: str) -> List[str]:
        from . import check as check_module
        from . import config as config_module
        return check_module.check(config_module.load(Path(project)))


@implementation("apply-esoi", "documents-templates-and-tools")
class DocumentsTemplatesAndTools:
    """The tools beside the documents: the structure check, the coherence of each intent's solutions, and the search that finds the
    records a request concerns (``spec-search``)."""

    def __init__(self, structure: StructureChecking):
        self.structure = structure

    def find(self, project: str, request: str) -> List[str]:
        """The keys of the project's records that ``request`` concerns, best first: ``spec-search`` over the views of its index, lexical
        only, so no model is called."""
        from . import config as config_module
        from . import spec_index, spec_search
        index = spec_index.build(config_module.load(Path(project)))
        return spec_search.lexical_only(request, spec_search.views_from_index(index)).ids

    def review(self, project: str) -> Dict[str, Any]:
        from collections import Counter
        problems = self.structure.check(project)
        report: Dict[str, Any] = {"problems": len(problems), "by_rule": dict(Counter(p.split(" ", 1)[0] for p in problems))}
        try:
            from . import coherence
            summary = coherence.check(Path(project))["summary"]
            report["coherence_passed"] = summary["passed"]
        except ImportError:
            report["coherence_passed"] = None
        return report


@implementation("implementation-selection", "declarations")
class Declarations:
    """The runtime cascade of ``esoi.runtime``: call, context, environment, deployment, then the records' default."""

    def choose(self, solution_id: str) -> Any:
        from . import runtime
        return runtime.choose(solution_id)


# The other solutions of esoi. Every entry reads a project (the path is the input) and writes nothing.

def loaded(project: str):
    """``(configuration, registry)`` of the project at ``project``."""
    from . import config as config_module
    from . import registry as registry_module
    cfg = config_module.load(Path(project))
    return cfg, registry_module.load(cfg)


@solution("intent-registry", kind="event", entry="count", example=".")
@runtime_checkable
class IntentRegistering(Protocol):
    """The project's records as the code reads them: how many rows each kind of record holds."""

    def count(self, project: str) -> Dict[str, int]: ...


def counted(found) -> Dict[str, int]:
    return {"problems": len(found.problems), "ideals": len(found.ideals), "solutions": len(found.every_solution()),
            "implementations": len(found.implementations), "metrics": len(found.metrics)}


@implementation("intent-registry", "esoi_folder")
class CsvRecords:
    """Records kept in the structure folder, one folder per intent (the layout before records beside the code)."""

    def count(self, project: str) -> Dict[str, int]:
        cfg, found = loaded(project)
        return counted(found)


@implementation("intent-registry", "beside_code")
class BesideCodeRecords:
    """Records kept beside the code they describe (`[records] beside_code` in esoi.toml), read as one tree with the structure folder."""

    def count(self, project: str) -> Dict[str, int]:
        cfg, found = loaded(project)
        return counted(found)


@solution("template-sync", kind="evaluate", entry="fields", example=".")
@runtime_checkable
class TemplateSyncing(Protocol):
    """The fields of each kind of record that the project's intent template asks for."""

    def fields(self, project: str) -> Dict[str, int]: ...


@implementation("template-sync", "template-parser")
class TemplateParser:
    """Reads the template from the parsed copy the repository keeps beside its records."""

    def fields(self, project: str) -> Dict[str, int]:
        from . import template
        cfg, found = loaded(project)
        return {entity: len(rows) for entity, rows in template.load_for(cfg).items()}


@solution("ownership-map", kind="evaluate", entry="unowned", example=".")
@runtime_checkable
class OwnershipMapping(Protocol):
    """The files of the project that no component owns."""

    def unowned(self, project: str) -> List[str]: ...


@implementation("ownership-map", "component-rows")
class ComponentRows:
    """The path patterns of the components table."""

    def unowned(self, project: str) -> List[str]:
        from . import check
        cfg, found = loaded(project)
        return sorted(name for name, owners in check.build_context(cfg).owners.items() if not owners)


@solution("measurement-harness", kind="event", entry="components", example=".")
@runtime_checkable
class MeasurementHarnessing(Protocol):
    """The components the project can measure, one per folder of cases and implementations."""

    def components(self, project: str) -> List[str]: ...


@implementation("measurement-harness", "component-harness")
class ComponentHarness:
    """The harness that runs each implementation over a component's cases, tells which recorded rows a change has made stale
    (``know-what-a-result-measures``) and reads the public evidence others measured (``public-evidence``)."""

    def components(self, project: str) -> List[str]:
        from . import harness
        cfg, found = loaded(project)
        return harness.discover_components(cfg)

    def stale(self, project: str) -> Dict[str, Dict[str, str]]:
        """Per staleness rule, which implementations' recorded rows a change has made stale (what ``esoi stale --count`` prints)."""
        from . import staleness
        cfg, found = loaded(project)
        return {rule: staleness.count_stale(cfg, rule) for rule in staleness.RULES}

    def public_evidence(self, project: str) -> int:
        """How many rows of public evidence the project holds beside its own measurements."""
        from . import evidence
        cfg, found = loaded(project)
        return len(evidence.load_for(cfg))


@solution("leaderboard", kind="evaluate", entry="standings", example=".")
@runtime_checkable
class Leaderboarding(Protocol):
    """How many recorded rows each measured component has in the project's results log."""

    def standings(self, project: str) -> Dict[str, int]: ...


@implementation("leaderboard", "margin-leaderboard")
class MarginLeaderboard:
    """The latest rows per component, ranked by pass rate with a margin."""

    def standings(self, project: str) -> Dict[str, int]:
        from . import leaderboard
        cfg, found = loaded(project)
        return {component: len(rows) for component, rows in leaderboard.latest_results(cfg.results_path).items()}


@solution("structure-rules", kind="evaluate", entry="rules", example=".")
@runtime_checkable
class StructureRuling(Protocol):
    """The ids of every rule that applies to the project, built in and from its plugins."""

    def rules(self, project: str) -> List[str]: ...


@implementation("structure-rules", "rule-modules")
class RuleModules:
    """Rule groups in modules, each declaring the ids it can report."""

    def rules(self, project: str) -> List[str]:
        from . import rules as rule_modules
        cfg, found = loaded(project)
        return list(rule_modules.summaries(cfg))


@solution("review-tracker", kind="evaluate", entry="stale", example=".")
@runtime_checkable
class ReviewTracking(Protocol):
    """The tracker tabs that are out of date with the records (empty when none is)."""

    def stale(self, project: str) -> List[str]: ...


@implementation("review-tracker", "tracker-and-sheet")
class TrackerAndSheet:
    """Tracker tabs written beside the records, and synced with a sheet on request."""

    def stale(self, project: str) -> List[str]:
        from . import tracker
        cfg, found = loaded(project)
        return [str(tab) for tab in tracker.stale(cfg, found)]


@solution("consumer-check", kind="event", entry="known_ids", example="esoi")
@runtime_checkable
class ConsumerChecking(Protocol):
    """The solution ids a consumer's registry may name for a library: how many the library defines."""

    def known_ids(self, library: str) -> Dict[str, Any]: ...


@implementation("consumer-check", "consumer-command")
class ConsumerCommand:
    """The consumer check that reads the library's own records or selection snapshot."""

    def known_ids(self, library: str) -> Dict[str, Any]:
        from . import consumer
        ids, full = consumer.known_solution_ids(consumer.Options(library=library))
        return {"solutions": len(ids), "from_records": full}


@solution("skill-distribution", kind="evaluate", entry="copies", example=".")
@runtime_checkable
class SkillDistributing(Protocol):
    """The committed copies of the author's skill: how many files each holds."""

    def copies(self, project: str) -> Dict[str, int]: ...


@implementation("skill-distribution", "generated-public-copy")
class GeneratedPublicCopy:
    """Copies generated from the private skill folder and checked for leaks."""

    def copies(self, project: str) -> Dict[str, int]:
        from . import skill
        cfg, found = loaded(project)
        return {folder.relative_to(cfg.root).as_posix(): len(skill.read_copy(folder)) for folder in skill.copy_folders(cfg, skill.settings_from(cfg))}


@solution("specify-from-code", kind="evaluate", entry="drift", example=".")
@runtime_checkable
class SpecifyingFromCode(Protocol):
    """The places where what the code declares and what the records say disagree."""

    def drift(self, project: str) -> List[str]: ...


@implementation("specify-from-code", "declarations-and-sync")
class DeclarationsAndSync:
    """@solution and @implementation declarations read from the code and compared with the records."""

    def drift(self, project: str) -> List[str]:
        from . import declarations
        cfg, found = loaded(project)
        return declarations.drift(cfg, found, declarations.scan(cfg))


@solution("readable-records", kind="evaluate", entry="page", example=".")
@runtime_checkable
class ReadableRecording(Protocol):
    """The README page of the project's top intent, generated from its records."""

    def page(self, project: str) -> str: ...


@implementation("readable-records", "full_page")
class FullPageReadme:
    """The record tables only, written from the records, so the page cannot disagree with them."""

    def page(self, project: str) -> str:
        from . import readme
        cfg, found = loaded(project)
        return readme.pages(cfg, found, layout="full")[0][1]


@implementation("readable-records", "at_a_glance")
class AtAGlanceReadme:
    """The summary a reader needs first (vision, coherence, diagram, entry calls, links), then the full record below a divider."""

    def page(self, project: str) -> str:
        from . import readme
        cfg, found = loaded(project)
        return readme.pages(cfg, found, layout="glance")[0][1]


@implementation("readable-records", "links_page")
class LinksPageReadme:
    """A compact page of the vision statement and links to everything else."""

    def page(self, project: str) -> str:
        from . import readme
        cfg, found = loaded(project)
        return readme.pages(cfg, found, layout="links")[0][1]


@solution("promote-the-winner", kind="evaluate", entry="proposals", example=".")
@runtime_checkable
class WinnerPromoting(Protocol):
    """What would be promoted now: each solution a rival clearly beats, with the status of the proposal. Nothing is changed."""

    def proposals(self, project: str) -> List[Tuple[str, str]]: ...


@implementation("promote-the-winner", "margin-promotion")
class MarginPromotion:
    """A rival that beats the selected implementation by the margin the solution's policy asks for."""

    def proposals(self, project: str) -> List[Tuple[str, str]]:
        from . import promote
        cfg, found = loaded(project)
        return [(one.solution_id, one.status) for one in promote.propose(cfg, found)]


@solution("keep-metric-record", kind="event", entry="readings", example=".")
@runtime_checkable
class MetricRecordKeeping(Protocol):
    """The two readings a piece of work records (before and after) and how each is said while it is taken."""

    def readings(self, project: str) -> Dict[str, str]: ...


@implementation("keep-metric-record", "library-modules")
class LibraryModules:
    """The iteration, meter and ledger modules of the library, over the slice of the specification that ``spec-index`` gives for the work."""

    def readings(self, project: str) -> Dict[str, str]:
        from . import iteration
        return {name: texts[0] for name, texts in iteration.READING_STATUS.items()}

    def slice_of(self, project: str, request: str, k: int = 5) -> List[str]:
        """The ids of the best ``k`` records of the project's index for the words of ``request``: the slice the work is measured against."""
        from . import config as config_module
        from . import spec_index
        index = spec_index.build(config_module.load(Path(project)))
        return [hit["id"] for hit in spec_index.find_specs(index, request, k)]


@solution("runtime-selection", kind="event", entry="layers", example="structure-check")
@runtime_checkable
class RuntimeSelecting(Protocol):
    """Every layer of the cascade that names an implementation for a solution, innermost first."""

    def layers(self, solution_id: str) -> List[Tuple[str, str, str]]: ...


@implementation("runtime-selection", "declarations-and-cascade")
class DeclarationsAndCascade:
    """The declarations of the code and the cascade call, context, environment, deployment, project."""

    def layers(self, solution_id: str) -> List[Tuple[str, str, str]]:
        from . import runtime
        return runtime.explain(solution_id, scope="esoi")


@solution("assemble-by-name", kind="event", entry="names", example="structure-check")
@runtime_checkable
class AssemblingByName(Protocol):
    """The implementation names a solution of esoi can be built from."""

    def names(self, solution_id: str) -> List[str]: ...


@implementation("assemble-by-name", "assembler")
class AssemblerByName:
    """An Assembler over esoi's own solutions."""

    def names(self, solution_id: str) -> List[str]:
        from .entry import own_runner
        return own_runner().assembler.names(solution_id)


# The solutions that are documents, judges and written processes. Each answers with a read-only fact about what it is made of; the
# model judges are measured by their components, so their one line reports the labelled cases they are graded on.

def count_cases(project: str, component: str) -> Dict[str, int]:
    from . import harness
    cfg, found = loaded(project)
    return {"cases": len(harness.load_cases(component, cfg))}


def read_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


def skill_file(project: str, name: str) -> Path:
    from . import skill
    cfg, found = loaded(project)
    return cfg.root / skill.settings_from(cfg).dir / name


@solution("behave-by-esoi", kind="event", entry="describe", example=".")
@runtime_checkable
class BehavingByEsoi(Protocol):
    """The cases an agent's replies are measured on to see whether they act by the principles."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("behave-by-esoi", "standing-instructions")
class StandingInstructions:
    """The skill given as standing instructions, measured case by case."""

    def describe(self, project: str) -> Dict[str, int]:
        return count_cases(project, "behave_by_esoi")


@solution("judge-esoi-behaviour", kind="event", entry="describe", example=".")
@runtime_checkable
class JudgingEsoiBehaviour(Protocol):
    """The labelled cases the grading of a reply is scored against."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("judge-esoi-behaviour", "model-judge")
class ModelJudge:
    """A model that grades one reply against one case; its agreement with the labels is the metric."""

    def describe(self, project: str) -> Dict[str, int]:
        return count_cases(project, "judge_esoi_behaviour")


@solution("esoi-behaviour-judge", kind="event", entry="describe", example=".")
@runtime_checkable
class EsoiBehaviourJudging(Protocol):
    """How many labelled replies show how far the judge's grading can be trusted."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("esoi-behaviour-judge", "model-judge-on-the-rubric")
class ModelJudgeOnTheRubric:
    """The judge graded against the labelled cases of its component: the cases the model judge it is built on (``judge-esoi-behaviour``)
    is scored against."""

    def __init__(self, judge: JudgingEsoiBehaviour):
        self.judge = judge

    def describe(self, project: str) -> Dict[str, int]:
        return self.judge.describe(project)


@solution("local-application-index", kind="event", entry="describe", example=".")
@runtime_checkable
class LocalApplicationIndexing(Protocol):
    """The cases the index of projects that apply ESOI is measured on."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("local-application-index", "live_index")
class LiveIndex:
    """The index folder in the user's home, measured on the cases of its component."""

    def describe(self, project: str) -> Dict[str, int]:
        return count_cases(project, "index_projects")


@solution("esoi-for-ai", kind="event", entry="describe", example=".")
@runtime_checkable
class EsoiForAi(Protocol):
    """The standing instructions an AI agent is given: the length of the skill that carries them."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("esoi-for-ai", "skill-as-standing-instructions")
class SkillAsStandingInstructions:
    """The public skill, loaded as standing instructions."""

    def describe(self, project: str) -> Dict[str, int]:
        return {"skill_lines": len(read_lines(skill_file(project, "SKILL.md")))}


@solution("the-steps", kind="event", entry="describe", example=".")
@runtime_checkable
class TheSteps(Protocol):
    """The title of the written order in which to define and apply ESOI."""

    def describe(self, project: str) -> Dict[str, str]: ...


@implementation("the-steps", "esoi-steps")
class EsoiSteps:
    """The steps file of the public skill."""

    def describe(self, project: str) -> Dict[str, str]:
        return {"title": next((line.lstrip("# ").strip() for line in read_lines(skill_file(project, "steps.md")) if line.startswith("#")), "")}


@solution("follow-the-steps", kind="event", entry="describe", example=".")
@runtime_checkable
class FollowingTheSteps(Protocol):
    """How many numbered steps the written order has."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("follow-the-steps", "steps")
class Steps:
    """The numbered lines of the steps file."""

    def describe(self, project: str) -> Dict[str, int]:
        import re
        return {"numbered_lines": sum(1 for line in read_lines(skill_file(project, "steps.md")) if re.match(r"\s*\d+[.)]\s", line))}


@solution("the-standard", kind="event", entry="describe", example=".")
@runtime_checkable
class TheStandard(Protocol):
    """The standard document that teaches how a solution is shaped: its length."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("the-standard", "standard-document")
class StandardDocument:
    """The standard document the template sync keeps in step with the skill."""

    def describe(self, project: str) -> Dict[str, int]:
        from . import template
        cfg, found = loaded(project)
        return {"standard_lines": len(read_lines(template.standard_doc_path(cfg)))}


@solution("docs-and-templates", kind="event", entry="describe", example=".")
@runtime_checkable
class DocsAndTemplates(Protocol):
    """How many how-to guides the documentation folder lists."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("docs-and-templates", "documentation-folder")
class DocumentationFolder:
    """The documentation folder and its index page."""

    def describe(self, project: str) -> Dict[str, int]:
        cfg, found = loaded(project)
        return {"how_to_guides": "\n".join(read_lines(cfg.root / "docs" / "README.md")).count("](how-to/")}


@solution("structure-budget", kind="event", entry="describe", example=".")
@runtime_checkable
class StructureBudgeting(Protocol):
    """What the structure costs the project now: its rules and its waivers."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("structure-budget", "written-weighing-rule")
class WrittenWeighingRule:
    """The rules and waivers counted, so each can be weighed against what it catches."""

    def describe(self, project: str) -> Dict[str, int]:
        from . import rules as rule_modules
        cfg, found = loaded(project)
        return {"rules": len(rule_modules.summaries(cfg)), "waivers": len(found.waivers)}


@solution("discriminating-cases", kind="event", entry="describe", example=".")
@runtime_checkable
class DiscriminatingCases(Protocol):
    """How many baseline implementations the components keep to prove their cases can tell a naive one from a sound one."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("discriminating-cases", "broken-baselines")
class BrokenBaselines:
    """The naive implementations kept in each component's ``broken/`` folder."""

    def describe(self, project: str) -> Dict[str, int]:
        cfg, found = loaded(project)
        files = sorted(cfg.evaluation.glob("*/broken/*.py")) if cfg.evaluation.is_dir() else []
        return {"baselines": sum(1 for file in files if file.name != "__init__.py")}


@solution("when-metrics-are-run", kind="event", entry="describe", example=".")
@runtime_checkable
class WhenMetricsAreRun(Protocol):
    """The length of the written policy that says when each metric is run and what it may spend."""

    def describe(self, project: str) -> Dict[str, int]: ...


@implementation("when-metrics-are-run", "on-every-change")
class OnEveryChange:
    """The policy page beside the records."""

    def describe(self, project: str) -> Dict[str, int]:
        cfg, found = loaded(project)
        return {"policy_lines": len(read_lines(cfg.structure / "metric-run-policy.md"))}
