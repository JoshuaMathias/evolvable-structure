"""One search over records and other items: lexical, semantic, gate, judge, links and the no-solution cue. Offline."""
import json

import pytest

from esoi import spec_search as ss


def entry(kind, id_, title, summary="", refs=(), intent="demo"):
    return {"id": id_, "kind": kind, "intent": intent, "title": title, "summary": summary, "refs": list(refs),
            "terms": ss.terms_of(title, summary)}


INDEX = {"version": 1, "n": 9, "df": {}, "entries": [
    entry("intent", "demo", "Reliable nightly invoices for small shops"),
    entry("problem", "prob-invoices-late", "Invoices arrive late", "Nightly invoice batch finishes after shops open.",
          refs=("sol-invoice-queue", "ideal-on-time")),
    entry("problem", "prob-refund-disputes", "Refund disputes pile up unanswered", "Nobody owns refund disputes.",
          refs=("ideal-on-time",)),
    entry("solution", "sol-invoice-queue", "Invoice batch queue", "Queue invoice generation per shop.",
          refs=("prob-invoices-late", "ideal-on-time", "metric-invoice-latency")),
    entry("ideal", "ideal-on-time", "On-time paperwork", "Every shop has its papers before opening.",
          refs=("prob-invoices-late", "prob-refund-disputes")),
    entry("metric", "metric-invoice-latency", "Invoice latency", "Minutes to the last invoice.", refs=("sol-invoice-queue",)),
    entry("implementation", "sol-invoice-queue:workers", "Worker pool", "Four workers.", refs=("sol-invoice-queue",)),
    entry("intent", "warehouse", "Warehouse robots that restock shelves", intent="warehouse"),
    entry("solution", "sol-tax-export", "Tax export file", "Export quarterly tax totals.", refs=()),
]}
ITEMS = {"runbook": {"name": "Invoice batch runbook", "summary": "Restart the nightly invoice batch, queue depth.",
                     "keywords": ["invoice", "batch"]},
         "keys": {"name": "Backup key rotation", "summary": "Rotate backup encryption keys monthly."}}


def views(tag_table=None):
    return ss.views_from_items(ITEMS, kind="card", source="cards") + ss.views_from_index(INDEX, tag_table)


class Judge:
    def __init__(self, reply=None, fail=False):
        self.reply, self.fail, self.calls, self.lines = reply, fail, 0, []

    def __call__(self, task, lines, limit):
        self.calls += 1
        self.lines.append(lines)
        if self.fail:
            raise RuntimeError("down")
        return self.reply


def test_keys_never_let_an_item_shadow_a_record():
    keys = [v.key for v in views()]
    assert "card:runbook" in keys and "sol-invoice-queue" in keys and len(set(keys)) == len(keys)


def test_lexical_ranks_items_and_records_together():
    ranked = ss.lexical_scored(views(), "nightly invoice batch queue", 5)
    assert {"card:runbook", "sol-invoice-queue"} <= {k for k, _ in ranked[:3]}
    assert ss.lexical_scored(views(), "zebra quokka marmalade", 5) == []
    assert all(k in ("sol-invoice-queue", "prob-invoices-late") for k, _ in ss.lexical_scored(views(), "invoice", 9, ("solution", "problem")))


def test_fuse_prefers_what_two_lists_share():
    assert ss.fuse([["a", "b"], ["c", "b"]], 3)[0] == "b"


def test_parse_ids_drops_unoffered_and_unreadable():
    assert ss.parse_ids('x {"ids": ["a", "zz", "a", "b"]}', {"a", "b"}) == ["a", "b"]
    assert ss.parse_ids("no json", {"a"}) is None
    assert ss.parse_ids('{"ids": "a"}', {"a"}) is None


def test_gate_decisions():
    assert ss.gate_decision([("a", 70.0)], [("a", 0.0)]) == "sure"
    assert ss.gate_decision([("a", 5.0)], [("a", 0.3)]) == "nothing"
    assert ss.gate_decision([("a", 30.0)], [("b", 0.6)]) == "ask"
    assert ss.gate_decision([("a", 30.0)], [("a", 0.0)]) == "ask"          # bare keys are never strong evidence
    assert ss.gate_decision([("a", 30.0)], [("a", 0.8)], ss.Gate(sure_vector=0.9)) == "ask"


def test_nothing_credible_costs_no_call():
    judge = Judge('{"ids": []}')
    got = ss.search("zebra quokka", views(), judge=judge)
    assert got.route == "nothing" and got.items == [] and judge.calls == 0


def test_sure_case_costs_no_call_and_brings_links():
    judge = Judge()
    vec = lambda text, k: [("sol-invoice-queue", 0.9)]   # noqa: E731
    got = ss.search("invoice batch queue per shop", views(), judge=judge, vector_search=vec)
    assert got.route == "sure" and judge.calls == 0
    assert got.items[0].key == "sol-invoice-queue" and got.linked["prob-invoices-late"] == "sol-invoice-queue"


def test_ambiguous_case_is_one_judged_call_and_keeps_only_offered_keys():
    judge = Judge('{"ids": ["card:runbook", "invented"]}')
    got = ss.search("nightly invoice batch", views(), judge=judge, expand=0)
    assert got.route == "judged" and got.calls == judge.calls == 1
    assert got.ids == ["card:runbook"]


def test_a_failing_or_unreadable_judge_keeps_the_best_candidates():
    for judge in (Judge(fail=True), Judge("not json")):
        got = ss.search("nightly invoice batch", views(), judge=judge, expand=0, unjudged_top=2)
        assert got.failed_batches == 1 and len(got.ids) == 2


def test_no_judge_returns_the_fused_candidates():
    got = ss.search("nightly invoice batch", views(), expand=0)
    assert got.route == "unjudged" and len(got.ids) == 3


def test_judge_may_answer_with_a_list():
    got = ss.search("nightly invoice batch", views(), judge=Judge(["sol-invoice-queue"]), expand=0)
    assert got.ids == ["sol-invoice-queue"]


def test_failing_vector_search_leaves_the_lexical_answer():
    def boom(text, k):
        raise RuntimeError("down")
    got = ss.search("invoice batch queue", views(), vector_search=boom, expand=0)
    assert got.ids and got.sources[got.ids[0]] == ["lexical"]


def test_judge_all_batches_every_candidate_and_keeps_a_failed_batch():
    seen = []

    def judge(task, lines, limit):
        seen.append(len(lines))
        if len(seen) == 1:
            raise RuntimeError("down")
        return ["x"]
    got = ss.search("invoice batch queue shop", views(), judge=judge, strategy="judge-all", batch_size=2, max_workers=1, expand=0)
    assert got.calls == len(seen) >= 2 and got.failed_batches == 1 and got.ids


def test_lexical_strategy_is_free():
    judge = Judge()
    got = ss.search("invoice batch queue", views(), judge=judge, strategy="lexical", expand=0)
    assert got.route == "lexical" and len(got.ids) <= 3 and judge.calls == 0


def test_no_solution_yet_is_set_for_an_unserved_problem_only():
    unserved = ss.search("refund disputes unanswered", views(), expand=0, ranked_kinds=("problem", "solution"))
    assert unserved.no_solution_yet == "prob-refund-disputes"
    served = ss.search("invoices arrive late", views(), expand=0, ranked_kinds=("problem", "solution"))
    assert served.no_solution_yet == "" and "no solution yet" not in ss.render(served)
    assert ss.render(unserved).startswith("NO SOLUTION YET for prob-refund-disputes")


def test_link_kinds_interleave_one_of_each_before_a_second():
    got = ss.search("invoice batch queue per shop", views(), vector_search=lambda t, k: [("sol-invoice-queue", 0.9)],
                    expand=3, link_kinds=("ideal", "metric", "intent", "implementation"))
    assert [i.key for i in got.items if i.linked_from] == ["ideal-on-time", "metric-invoice-latency", "demo"]


def test_tags_boost_or_filter():
    table = ss.TagTable(tag_problems={"paperwork": ("prob-refund-disputes",)}, solution_tags={"sol-tax-export": ("paperwork",)})
    kinds = ("problem", "solution")
    plain = ss.search("export refund invoices", views(table), expand=0, ranked_kinds=kinds, unjudged_top=9, gate=ss.Gate(nothing_lexical=0.0))
    kept = ss.search("export refund invoices", views(table), expand=0, ranked_kinds=kinds, unjudged_top=9, gate=ss.Gate(nothing_lexical=0.0), tags=["paperwork"],
                     tag_mode="filter")
    assert set(kept.ids) == {"prob-refund-disputes", "sol-tax-export"} < set(plain.ids)


def test_bad_arguments_fail_loudly():
    with pytest.raises(ValueError):
        ss.search("x", views(), strategy="magic")
    with pytest.raises(ValueError):
        ss.search("x", views(), tag_mode="magic")


def test_the_index_json_round_trips_into_views(cfg):
    from esoi import spec_index
    built = json.loads(json.dumps(spec_index.build(cfg)))
    found = ss.search("greet", ss.views_from_index(built), expand=0)
    assert isinstance(found, ss.Selection)


def test_the_solution_selects_an_implementation_by_name():
    assert ss.search("invoice batch queue", views(), using="lexical-only", expand=0).route == "lexical"
    assert ss.search("invoice batch queue", views(), using="lexical-vector-gated", expand=0).route == "unjudged"
