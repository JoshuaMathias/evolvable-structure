"""The generated non-code templates and excerpts."""
from esoi import templates
from esoi.config import Config
from test_template import SAMPLE

SKILL = """---
name: x
---

# evolvable-structure

An opening paragraph.

## Purpose

The first purpose paragraph.

Private instructions for tools that must not be quoted.

## Background

About the author.

## Definitions
- **Evolvable:** Changeable.

""" + SAMPLE.split("# A skill\n\n")[1].replace("## Principles\n", "") + """
Remember: x

## Principles (Ideals)
1. **First.** Text.
"""


def make(tmp_path):
    source = tmp_path / "SKILL.md"
    source.write_text(SKILL)
    cfg = Config(root=tmp_path, template_source="SKILL.md", structure_dir="structure", templates_dir="docs/templates",
                 excerpts_file="docs/explanation/from-the-skill.md")
    (tmp_path / "structure").mkdir()
    return cfg


def test_sync_writes_every_generated_file_and_check_agrees(tmp_path):
    cfg = make(tmp_path)
    assert templates.sync(cfg, say=lambda text: None) == 0
    for name in ("problem.md", "solution.md", "overall-solution-network.md", "repository-standard.md", "review-sheet.md",
                 "record-headers/solutions.csv", "record-headers/results.csv"):
        assert (tmp_path / "docs" / "templates" / name).exists(), name
    assert (tmp_path / "structure" / "esoi_template.csv").exists()
    assert templates.sync(cfg, check=True, say=lambda text: None) == 0


def test_a_refined_source_makes_the_copies_stale(tmp_path):
    cfg = make(tmp_path)
    templates.sync(cfg, say=lambda text: None)
    (tmp_path / "SKILL.md").write_text(SKILL.replace("What is the problem?", "What exactly is the problem?"))
    lines = []
    assert templates.sync(cfg, check=True, say=lines.append) == 1 and "problem.md" in lines[-1]


def test_a_missing_source_is_reported(tmp_path):
    cfg = Config(root=tmp_path, template_source="nothing.md")
    lines = []
    assert templates.sync(cfg, say=lines.append) == 2 and "not found" in lines[0]


def test_the_entity_template_quotes_the_questions_and_the_definition(tmp_path):
    cfg = make(tmp_path)
    templates.sync(cfg, say=lambda text: None)
    text = (tmp_path / "docs" / "templates" / "problem.md").read_text()
    assert "_What is the problem?_" in text and "> What motivated the intent." in text and "edit `SKILL.md`" in text


def test_the_excerpts_quote_only_the_public_parts(tmp_path):
    text = templates.excerpts(SKILL)
    assert "An opening paragraph." in text and "The first purpose paragraph." in text and "Changeable." in text
    assert "must not be quoted" not in text and "About the author" not in text and "1. **First.** Text." in text


def test_record_headers_start_with_the_key_and_end_with_the_parent_links():
    rows, _ = templates.parse(SAMPLE)
    headers = templates.record_headers(rows)
    assert headers["solutions.csv"].startswith("solution_id,name,goals,parameters")
    assert headers["solutions.csv"].strip().endswith("parent_metric_ids")
    assert headers["components.csv"].startswith("component_id,layer")


def test_the_solutions_header_carries_every_column_the_rules_read():
    """Rules S7 and S14 read `port`; a repository that copies the header must not lose it."""
    from esoi.registry import OPTIONAL_COLUMNS, RULE_COLUMNS
    rows, _ = templates.parse(SAMPLE)
    header = templates.record_headers(rows)["solutions.csv"].strip().split(",")
    assert set(RULE_COLUMNS["solutions.csv"] + OPTIONAL_COLUMNS["solutions.csv"]) <= set(header)
    assert set(RULE_COLUMNS["components.csv"]) == set(templates.record_headers(rows)["components.csv"].strip().split(","))
    assert set(RULE_COLUMNS["waivers.csv"]) == set(templates.record_headers(rows)["waivers.csv"].strip().split(","))
