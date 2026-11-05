"""The generated pages of a hierarchy: an intent page lists its children by kind, a leaf solution page ends the hierarchy by having no children,
a solution page shows its own purpose and its immediate parent (never an ancestor's vision), and every page opens with a breadcrumb and ends with
the generated note."""
from conftest import fill_top_intent  # noqa: F401  (the cfg fixture fills the top intent)
from esoi.structure.intent_registry import config, intents, registry
from esoi.understanding.readable_records import readme, readme_view
from test_intents import add_solution, rewrite, write_intent


def hierarchy(cfg):
    """Three levels: the root intent, the sub-intent ``voices`` beside the code, and a leaf solution with arms inside it; plus a leaf solution
    directly under the root, so the root lists both kinds."""
    root_leaf = cfg.root / cfg.package_dir / "greeter"
    root_leaf.mkdir()
    add_solution(cfg, root_leaf, "greet-loudly", "by-shout")
    voices = cfg.root / cfg.package_dir / "voices"
    write_intent(voices, "voices", "greet-a-person:live")
    leaf = voices / "inner"
    leaf.mkdir()
    add_solution(cfg, leaf, "speak-a-greeting", "by-voice")
    toml = cfg.root / "esoi.toml"
    patterns = f'["{cfg.package_dir}", "{cfg.package_dir}/*", "{cfg.package_dir}/voices/*"]'
    toml.write_text(toml.read_text().replace("records.template_version", f"records.beside_code = {patterns}\nrecords.template_version", 1))
    rewrite(cfg.structure / "implementations.csv", lambda rows, cols: [r.update(sub_intent="voices" if r["implementation_id"] == "greet-a-person:live" else "") for r in rows])
    after = config.load(cfg.root)
    loaded = registry.load(after)
    return after, loaded, dict(readme.pages(after, loaded)), root_leaf, voices, leaf


def test_the_parent_lists_each_child_with_a_link_and_its_kind_and_the_vision_or_purpose(cfg):
    after, loaded, pages, root_leaf, voices, leaf = hierarchy(cfg)
    root = pages[after.structure / "README.md"]
    below = root.split("## One level below\n", 1)[1].split("\n## ", 1)[0]
    assert "- [Voices](../demo/voices/README.md) (sub-intent): The voices are spoken well." in below
    greet = next(r for r in loaded.every_solution() if r["solution_id"] == "greet-loudly")
    assert f"(solution with implementations): {' '.join(greet['purpose'].split())}" in below
    assert "(solution with no page of its own, its implementations are in this intent's records)" in below
    inner = pages[voices / "README.md"].split("## One level below\n", 1)[1]
    assert "inner/README.md) (solution with implementations)" in inner


def test_a_leaf_solution_page_has_its_implementations_and_no_children_and_does_not_announce_it_is_the_bottom(cfg):
    after, loaded, pages, root_leaf, voices, leaf = hierarchy(cfg)
    text = pages[leaf / "README.md"]
    assert "## One level below" not in text and "Bottom of the hierarchy" not in text and "Sub-intent" not in text
    table = text.split("## Implementations\n", 1)[1]
    assert "| Implementation | Handle | Purpose | Code | Selected |" in table and "| `speak-a-greeting:by-voice` | Spoken. |" in table


def test_every_page_has_a_breadcrumb_with_links_to_each_ancestor_and_a_leaf_names_its_immediate_parent(cfg):
    after, loaded, pages, root_leaf, voices, leaf = hierarchy(cfg)
    assert "Breadcrumb: [Top](../../../esoi/README.md) > [Voices](../README.md) > Project structure\n" in pages[leaf / "README.md"]
    assert "Part of [Voices](../README.md)" in pages[leaf / "README.md"]
    assert "Breadcrumb: [Top](../../esoi/README.md) > Voices\n" in pages[voices / "README.md"]
    assert "Breadcrumb: Top\n" in pages[after.structure / "README.md"]
    assert "Part of [Consistent greetings](../../esoi/README.md)" in pages[root_leaf / "README.md"]


def test_a_solution_page_shows_its_own_purpose_and_never_a_vision_of_the_intent_above(cfg):
    after, loaded, pages, root_leaf, voices, leaf = hierarchy(cfg)
    text = pages[leaf / "README.md"]
    purpose = " ".join(next(r for r in loaded.every_solution() if r["solution_id"] == "speak-a-greeting")["purpose"].split())
    assert f"**Purpose:** {purpose}" in text
    top = next(i for i in intents.discover(after) if i.is_top)
    assert "Vision statement" not in text and "The voices are spoken well." not in text and top.row["vision_statement"] not in text
    assert "These are the solutions of" not in text


def test_a_folder_two_levels_below_the_root_names_the_nearest_intent_not_the_root(cfg):
    after, loaded, pages, root_leaf, voices, leaf = hierarchy(cfg)
    text = pages[leaf / "README.md"]
    top = next(i for i in intents.discover(after) if i.is_top)
    assert "Part of [Voices]" in text and f"Part of [{top.row['name']}]" not in text
    assert top.row["name"] not in text


def test_a_generated_note_closes_every_page_and_is_never_at_the_top(cfg):
    after, loaded, pages, root_leaf, voices, leaf = hierarchy(cfg)
    for path, text in pages.items():
        assert text.rstrip().endswith(readme_view.GENERATED_NOTES), path
        assert not text.startswith("*") and "generated from the csv" not in text[:text.rindex("\n*Generated")].lower(), path
