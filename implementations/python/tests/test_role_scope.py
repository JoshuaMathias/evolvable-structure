"""Rules S48 and S49: the role of a solution against its siblings, informing only (what it is not responsible for and who owns that,
overlap of purposes, the change driver of a container) and the review prompt for implementations that may serve different purposes."""
from types import SimpleNamespace

from esoi.rules import intents as rules


def ctx(solutions, implementations=(), waivers=()):
    registry = SimpleNamespace(every_solution=lambda: solutions, implementations=list(implementations))
    return SimpleNamespace(registry=registry, waived=lambda rule, key: (rule, key) in set(waivers))


def sol(sid, **more):
    return dict({"solution_id": sid, "name": sid.title(), "intent_id": "demo", "purpose": "", "description": "", "out_of_scope": "x", "delegates_to": "none"}, **more)


def test_a_solution_with_siblings_and_no_exclusions_is_informed():
    found = rules.role_scope(ctx([sol("mind", out_of_scope=""), sol("body")]))
    assert len(found) == 1 and found[0].startswith("S48 mind:") and "NOT responsible" in found[0] and "delegates_to" in found[0]
    assert rules.role_scope(ctx([sol("mind", out_of_scope="")])) == []                       # no sibling, nothing to scope against


def test_exclusions_with_no_named_owner_are_informed_once_the_repository_records_delegation():
    group = [sol("mind", out_of_scope="Moving anything.", delegates_to=""), sol("body")]
    found = rules.role_scope(ctx(group))
    assert any(line.startswith("S48 mind:") and "who owns it" in line for line in found)
    assert not rules.role_scope(ctx([sol("mind", out_of_scope="Moving anything: Body owns it.", delegates_to=""), sol("body")]))   # names a sibling
    assert not rules.role_scope(ctx([sol("mind", out_of_scope="Moving anything.", delegates_to="body"), sol("body")]))              # delegates to one
    assert not rules.role_scope(ctx([sol("mind", out_of_scope="Moving anything.", delegates_to="none"), sol("body")]))              # says nothing is delegated


def test_a_repository_that_does_not_record_delegation_gets_one_prompt_per_intent_not_one_per_solution():
    plain = [{k: v for k, v in sol(s).items() if k != "delegates_to"} for s in ("mind", "body", "world")]
    found = rules.role_scope(ctx(plain))
    assert len(found) == 1 and found[0].startswith("S48 demo:") and "delegates_to" in found[0] and "scope-the-role" in found[0]


def test_delegating_to_something_that_is_no_solution_is_informed():
    found = rules.role_scope(ctx([sol("mind", delegates_to="ghost"), sol("body")]))
    assert any("delegates_to names ghost, which is no solution" in line for line in found)


def test_two_siblings_with_strongly_overlapping_purposes_are_informed_and_a_waiver_excuses_the_pair():
    text = "Carries out a goal by running a coding agent over the files of a repository and reporting the result"
    group = [sol("acting", purpose=text, description="Edits files"), sol("coding", purpose=text + " carefully", description="Edits files")]
    found = [line for line in rules.role_scope(ctx(group)) if "+" in line.split(":")[0]]
    assert len(found) == 1 and found[0].startswith("S48 acting+coding:") and "merge" in found[0] and "delegate" in found[0]
    assert not [line for line in rules.role_scope(ctx(group, waivers=[("S48", "acting+coding")])) if "+" in line.split(":")[0]]
    other = [sol("acting", purpose=text), sol("billing", purpose="Charges customers monthly and issues invoices with receipts attached")]
    assert not [line for line in rules.role_scope(ctx(other)) if "+" in line.split(":")[0]]


def test_a_container_must_name_what_kind_of_change_moves_its_metric():
    impls = [{"solution_id": "mind", "implementation_id": "mind:inner", "sub_intent": "inner"}]
    found = rules.role_scope(ctx([sol("mind"), sol("body")], impls))
    assert any(line.startswith("S48 mind:") and "change_driver" in line and "ML task accuracy" in line for line in found)
    assert not [line for line in rules.role_scope(ctx([sol("mind", change_driver="outside systems"), sol("body")], impls)) if "change_driver" in line]


def test_implementations_with_little_in_common_get_a_review_prompt_and_alike_ones_do_not():
    unlike = [{"solution_id": "acting", "implementation_id": f"acting:{n}", "name": n, "description": d} for n, d in (
        ("One-call edit", "writes one file with a single request"), ("MCP write", "forwards an operation to a connected server"),
        ("Claude Code runner", "launches a coding agent that carries out an open goal across a repository"))]
    found = rules.review_prompts(ctx([], unlike))
    assert len(found) == 1 and found[0].startswith("S49 acting:") and "review prompt" in found[0] and "SAME job" in found[0] and "MCP write" in found[0]
    alike = [{"solution_id": "store", "implementation_id": f"store:{n}", "name": n, "description": "keeps cards in a local store on disk and finds cards by meaning"}
             for n in ("memory", "disk", "sqlite")]
    assert rules.review_prompts(ctx([], alike)) == []
    assert rules.review_prompts(ctx([], unlike[:2])) == []                                  # two arms are not enough to read as a list
    assert rules.review_prompts(ctx([], unlike, waivers=[("S49", "acting")])) == []
