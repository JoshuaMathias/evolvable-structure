"""Reading the intent template from markdown."""
from pathlib import Path

from esoi import records, template

SAMPLE = """# A skill

Intent template definitions (each intent can have multiple items):
- **Problem**: What motivated the intent.
    Specify:
        - What is the problem?
        - Who or what type of person has the problem?
        - Why does this problem matter?
    What it's not: A task.
    Connects to: **Ideals**
- **Solution**: A definition of how a problem is addressed.
    Specify:
        - Name: What is it called?
        - Milestones: What are the priorities in order?
            Each milestone is a value of one or more metrics.
            End condition: Condition for the milestone to stop being a priority.
    If technology, specify interface details where applicable:
        - Parameters
        - Inputs
- **Metric**: A way to measure.
    Specify:
        - Name: What is measured?
        -

## Principles
"""


def keys(rows, entity, group="specify"):
    return [r["field_key"] for r in rows if r["entity"] == entity and r["group"] == group]


def test_parse_reads_fields_groups_and_meta():
    rows, notes = template.parse(SAMPLE)
    assert keys(rows, "problem") == ["problem", "who_has_it", "why_it_matters"]
    assert keys(rows, "solution") == ["name", "milestones"] and keys(rows, "solution", "interface") == ["parameters", "inputs"]
    meta = {r["field_key"]: r["question"] for r in rows if r["entity"] == "problem" and r["group"] == "meta"}
    assert meta["what_it_is_not"] == "A task." and "Ideals" in meta["connects_to"]
    assert any("empty bullet" in n for n in notes) and any("implementation: section missing" in n for n in notes)


def test_lines_indented_under_a_field_are_guidance_for_that_field_not_new_fields():
    rows, _ = template.parse(SAMPLE)
    assert keys(rows, "solution") == ["name", "milestones"]
    question = next(r["question"] for r in rows if r["entity"] == "solution" and r["field_key"] == "milestones")
    assert question.startswith("What are the priorities in order?")
    assert "Each milestone is a value of one or more metrics." in question and "End condition: Condition" in question
    assert len(rows) == len({(r["entity"], r["field_key"]) for r in rows})


def test_a_missing_block_parses_to_nothing():
    rows, notes = template.parse("# nothing\n")
    assert rows == [] and "no 'Intent specification' block" in notes[0]


def test_the_shipped_copy_matches_what_the_parser_makes_of_its_own_rows():
    shipped = records.load_template()
    assert set(shipped) == set(template.ENTITIES)
    assert "who_has_it" in [r["field_key"] for r in shipped["problem"]]


def test_render_and_read_round_trip(tmp_path):
    rows, _ = template.parse(SAMPLE)
    path = tmp_path / "t.csv"
    path.write_text(template.render_template_csv(rows))
    loaded = records.load_template(path)
    assert [r["field_key"] for r in loaded["solution"]] == [r["field_key"] for r in rows if r["entity"] == "solution"]


def test_apply_section_replaces_only_between_the_markers():
    rows, _ = template.parse(SAMPLE)
    section = template.render_section(rows)
    document = f"before\n{template.START}\nOLDTEXT\n{template.END}\nafter\n"
    updated = template.apply_section(document, section)
    assert updated.startswith("before\n") and updated.endswith("\nafter\n") and "OLDTEXT" not in updated
    assert template.apply_section("no markers\n", section) == "no markers\n"


def test_load_for_prefers_the_repository_copy(cfg):
    assert template.load_for(cfg)["problem"]
    template.template_csv_path(cfg).write_text("entity,field_key,question,group,required\nproblem,only,Q,specify,yes\n")
    assert [r["field_key"] for r in template.load_for(cfg)["problem"]] == ["only"]


def test_stale_against_source_is_none_when_the_source_is_unreachable(cfg):
    assert template.stale_against_source(cfg) is None
    source = Path(cfg.root) / "SKILL.md"
    source.write_text(SAMPLE)
    cfg.template_source = "SKILL.md"
    assert template.stale_against_source(cfg) is True


def test_optional_marker_is_read_per_field_and_stripped_from_the_name():
    from esoi import template
    text = ("Intent specification:\n- **Solution**: A way.\n    - Specify:\n        - Name: What is it called?\n"
            "        - Knowledge (optional): What informs it?\n")
    rows, _ = template.parse(text)
    got = {r["field_key"]: (r["required"], r["question"]) for r in rows if r["entity"] == "solution"}
    assert got["name"][0] == "yes" and got["knowledge"] == ("no", "What informs it?")


def test_optional_marker_may_carry_a_note_after_a_semicolon():
    from esoi import template
    text = ("Intent specification:\n- **Metric**: A measure.\n    - Specify:\n        - Name: What is measured?\n"
            "        - Cascading Conditionals (optional; for any case where the metric is costly): If given, run in order.\n")
    rows, notes = template.parse(text)
    got = {r["field_key"]: (r["required"], r["question"]) for r in rows if r["entity"] == "metric"}
    assert got["cascading_conditionals"] == ("no", "If given, run in order.")
    assert not [n for n in notes if "BARE_KEYS" in n]
