"""The Solution Diagram and Solution Coherence: the diagram is drawn from the records, a coherence paragraph that leaves a solution
out is a note, and a solution is motivated by a problem of its own intent."""
from conftest import fill_top_intent
from esoi import check, diagram, intents, registry, tables
from test_intents import add_solution, add_sub_intent, lines, rewrite


def clear_uses(cfg):
    rewrite(cfg.structure / "implementations.csv", lambda rows, cols: [r.update(uses_solution_ids="") for r in rows])


def test_an_edge_runs_from_the_solution_that_provides_to_the_one_that_builds_on_it(cfg):
    rewrite(cfg.structure / "solutions.csv", lambda rows, cols: [r.update(outputs='A "greeting" line.') for r in rows
                                                                 if r["solution_id"] == "greet-a-person"])
    loaded = registry.load(cfg)
    assert diagram.edges(loaded, "demo")[("greet-a-person", "project-purpose")] == "A 'greeting' line"
    page = diagram.render(loaded, intents.discover(cfg)[0])
    assert "```mermaid" in page and "flowchart LR" in page and '-->|"A \'greeting\' line"|' in page
    drawing = page[page.index("```mermaid"):]   # the paragraph above it names the solutions in its own order
    assert drawing.index("greet-a-person") < drawing.index("project-purpose")


def test_an_intent_without_a_dependency_has_no_diagram_and_a_stale_one_is_reported_and_written(cfg):
    assert diagram.stale(cfg, registry.load(cfg)) == [] and (cfg.structure / "diagram.md").exists()   # the scaffold writes it
    (cfg.structure / "diagram.md").write_text("edited by hand\n")
    assert any(line.startswith("S8") and "diagram.md" in line for line in check.check(cfg))
    assert diagram.run_cli(cfg, check=True, say=lambda text: None) == 1
    assert diagram.run_cli(cfg, say=lambda text: None) == 0
    assert diagram.run_cli(cfg, check=True, say=lambda text: None) == 0 and not lines(cfg, "S8")
    clear_uses(cfg)
    loaded = registry.load(cfg)
    assert diagram.render(loaded, intents.discover(cfg)[0]) == "" and diagram.stale(cfg, loaded) == [cfg.structure / "diagram.md"]
    diagram.write(cfg, loaded, say=lambda text: None)
    assert not (cfg.structure / "diagram.md").exists()


def test_a_coherence_paragraph_that_leaves_a_solution_out_is_a_note_not_an_error(cfg):
    assert check.notes(cfg) == []
    rewrite(cfg.structure / "intent.csv", lambda rows, cols: [r.update(solution_coherence="Only project-purpose matters.") for r in rows])
    found = [n for n in check.notes(cfg) if "solution_coherence" in n]
    assert len(found) == 1 and "greet-a-person" in found[0] and "project-structure" in found[0] and "project-purpose" not in found[0]
    assert not lines(cfg, "S28")
    named = "GREETING by name: Greetings sent (project-purpose), greet-a-person and project-structure."
    rewrite(cfg.structure / "intent.csv", lambda rows, cols: [r.update(solution_coherence=named) for r in rows])
    assert not [n for n in check.notes(cfg) if "solution_coherence" in n]


def test_a_blank_coherence_is_an_unfilled_field_but_a_blank_diagram_is_fine(cfg):
    rewrite(cfg.structure / "intent.csv", lambda rows, cols: [r.update(solution_coherence="") for r in rows])
    assert any(line.startswith("S28") and "solution_coherence" in line and "solution_diagram" not in line for line in check.check(cfg))


def test_a_solution_needs_a_problem_of_its_own_intent_not_only_its_parents(cfg):
    sub = add_sub_intent(cfg)
    add_solution(cfg, sub, "speak-it", "aloud")
    assert not lines(cfg, "S26")
    rewrite(sub / "solutions.csv", lambda rows, cols: [r.update(problem_ids="greeting-by-hand") for r in rows])
    rewrite(sub / "problems.csv", lambda rows, cols: [r.update(solution_ids="") for r in rows])
    found = lines(cfg, "S26")
    assert any("speak-it: addresses no problem of its own intent voices" in line for line in found)
