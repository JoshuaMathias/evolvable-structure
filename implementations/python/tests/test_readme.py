"""The README of an intent folder: the at-a-glance layout, links that resolve, stale pages reported, and the rival layouts."""
import re

import pytest
from conftest import fill_top_intent  # noqa: F401  (the cfg fixture fills the top intent)
from esoi import check, config, intents, readme, registry
from test_intents import add_sub_intent, lines, rewrite


def page(cfg, layout=None, which=0):
    loaded = registry.load(cfg)
    view = readme.view_of(cfg, loaded)
    return readme.render(loaded, view.intents[which], view, layout)


def test_the_glance_page_opens_with_name_vision_coherence_and_the_diagram_and_keeps_the_full_record_below_a_divider(cfg):
    text = page(cfg)
    top, _, record = text.partition("\n---\n")
    assert top.startswith("# Consistent greetings\n\nEvery person is greeted by their own name.")
    for part in ("## How the solutions fit together", "## Diagram", "```mermaid", "## Solutions at a glance", "## Problems and ideals",
                 "## Metrics and their leaders", "## Where to go next"):
        assert part in top
    assert top.index("## How the solutions fit together") < top.index("## Diagram") < top.index("## Solutions at a glance")
    assert "### Problems" in record and "### Implementations" in record and "### Solutions" in record and "| Implementation |" not in top


def test_a_solution_row_carries_its_entry_call_or_says_none_is_declared_and_its_selected_implementation(cfg):
    text = page(cfg)
    row = next(ln for ln in text.splitlines() if ln.startswith("| `greet-a-person`") and "Selected" not in ln and "run(" in ln or "no entry declared" in ln)
    assert "no entry declared" in row or "run(\"greet-a-person\"" in row
    assert "none selected" in text or "`" in row


def test_the_page_links_the_sub_intent_down_the_parent_up_and_the_repository_readme(cfg):
    sub = add_sub_intent(cfg)
    top = page(cfg, which=0)
    assert "[Greeting voices](voices/README.md)" in top or "(voices/README.md)" in top
    below = page(cfg, which=1)
    assert "(../README.md)" in below
    assert "[top README](../../README.md)" in below


def test_every_relative_link_of_every_layout_resolves(cfg):
    add_sub_intent(cfg)
    (cfg.root / "README.md").write_text("# project\n")
    for layout in readme.LAYOUTS:
        for index, intent in enumerate(intents.discover(cfg)):
            for target in re.findall(r"(?<!!)\[[^\]]*\]\(([^)\s#]+)", page(cfg, layout, index)):
                if "://" in target:
                    continue
                folder = intent.folder
                found = (folder / target).resolve()
                assert found.exists() or any(i.folder.resolve() / "README.md" == found for i in intents.discover(cfg)), (layout, target)


def test_a_stale_page_is_reported_by_the_command_and_by_rule_s8_and_the_command_writes_it(cfg):
    assert readme.run_cli(cfg, check=True, say=lambda text: None) == 0
    path = cfg.structure / "README.md"
    path.write_text("edited by hand\n")
    said = []
    assert readme.run_cli(cfg, check=True, say=said.append) == 1 and "out of date" in said[0]
    assert any(line.startswith("S8") and "README.md" in line for line in check.check(cfg))
    assert readme.run_cli(cfg, say=lambda text: None) == 0
    assert readme.run_cli(cfg, check=True, say=lambda text: None) == 0 and not lines(cfg, "S8")
    assert path.read_text() == page(cfg)


def test_check_write_docs_writes_the_same_page_as_the_command(cfg):
    (cfg.structure / "README.md").unlink()
    check.write_docs(cfg)
    assert (cfg.structure / "README.md").read_text() == page(cfg)


def test_generating_twice_gives_the_same_text_and_the_page_has_no_em_dash_or_machine_path(cfg):
    assert page(cfg) == page(cfg)
    assert chr(0x2014) not in page(cfg) and "/home/" not in page(cfg)


def test_a_cell_that_holds_only_an_unconfirmed_marker_is_left_out_of_the_page(cfg):
    rewrite(cfg.structure / "problems.csv", lambda rows, cols: [r.update(problem="unconfirmed: for a person to confirm.") for r in rows])
    rewrite(cfg.structure / "ideals.csv", lambda rows, cols: [r.update(principle="Unconfirmed, from the call: Greet by name.") for r in rows])
    text = page(cfg)
    assert "unconfirmed" not in text.lower() and "Greet by name." in text


def test_a_long_short_list_is_capped_and_points_at_the_full_record(cfg):
    from esoi import tables
    path = cfg.structure / "problems.csv"
    rows, cols = tables.read_csv(path), tables.read_header(path)
    for n in range(readme.LIST_LIMIT + 3):
        rows.append(dict(rows[0], problem_id=f"extra-{n}", problem=f"Extra problem {n}. More."))
    tables.write_csv(path, cols, rows)
    top = page(cfg).partition("\n---\n")[0]
    assert "more: all" in top and "(#problems)" in top and top.count("- `extra-") <= readme.LIST_LIMIT


def test_the_full_and_links_layouts_are_rivals_chosen_by_configuration(cfg):
    assert "\n---\n" not in page(cfg, "full") and "## Problems" in page(cfg, "full")
    compact = page(cfg, "links")
    assert "## Go to" in compact and "## Problems" not in compact and "```mermaid" not in compact
    cfg.readme = {"layout": "links"}
    assert page(cfg) == compact
    with pytest.raises(ValueError):
        readme.layout_of(cfg, "nonsense")


def test_the_diagram_in_the_page_is_the_diagram_page_source(cfg):
    from esoi import diagram
    loaded = registry.load(cfg)
    intent = intents.discover(cfg)[0]
    assert "\n".join(diagram.block(loaded, intent)) in page(cfg) and "\n".join(diagram.block(loaded, intent)) in diagram.render(loaded, intent)


def test_a_declared_entry_shows_as_the_one_line_call_with_its_example(cfg):
    (cfg.root / "demo" / "seat.py").write_text('"""A seat."""\nfrom esoi import solution\n\n\n'
                                               '@solution("greet-a-person", kind="event", entry="greet", example="Ada")\n'
                                               'class Greeting:\n    """Greets."""\n')
    text = page(cfg)
    assert 'demo.run("greet-a-person", \'Ada\')' in text


def test_the_declarations_of_esois_own_modules_are_read_through_their_relative_import():
    from esoi import declarations
    seen = declarations.Declared()
    declarations.scan_file("pkg/seat.py", 'from .runtime import solution\n\n\n@solution("one", kind="event", entry="go", example="x")\nclass One:\n    """One."""\n', seen)
    assert seen.solutions["one"].entry == "go" and seen.solutions["one"].example == "x"
