"""esoi.docs: the four-category standard, link checking and the generated wiki."""
from pathlib import Path

from esoi import docs

ROOT = Path(__file__).resolve().parents[3]


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sample(tmp_path: Path) -> Path:
    write(tmp_path, "docs/README.md", "# Home\n\n## Start\n\n- [Learn](tutorials/first.md)\n- [Do](how-to/do-it.md)\n")
    write(tmp_path, "docs/tutorials/first.md", "# First steps: a tutorial\n\nSee [the how-to](../how-to/do-it.md).\n")
    write(tmp_path, "docs/how-to/do-it.md", "# Do it\n\nSee [why](../explanation/why.md) and [code](../../src/x.py).\n")
    write(tmp_path, "docs/explanation/why.md", "# Why\n\nText.\n")
    write(tmp_path, "docs/reference/facts.md", "# Facts\n\nText.\n")
    write(tmp_path, "src/x.py", "x = 1\n")
    return tmp_path


def test_a_well_formed_docs_folder_passes(tmp_path):
    assert docs.check(sample(tmp_path)) == []


def test_a_page_outside_the_four_folders_is_reported(tmp_path):
    root = sample(tmp_path)
    write(root, "docs/guides/old.md", "# Old\n")
    write(root, "docs/loose.md", "# Loose\n")
    found = docs.check(root)
    assert any("guides/old.md" in p and "outside" in p for p in found) and any("loose.md" in p for p in found)


def test_a_broken_link_is_reported_but_code_samples_and_urls_are_not(tmp_path):
    root = sample(tmp_path)
    write(root, "docs/explanation/why.md", "# Why\n\n[gone](missing.md) [web](https://example.org/a.md) `[x](nope.md)`\n\n```\n[y](nope2.md)\n```\n")
    found = docs.check(root)
    assert found == ["docs/explanation/why.md: link to missing.md does not resolve"]


def test_a_missing_index_is_reported(tmp_path):
    root = sample(tmp_path)
    (root / "docs" / "README.md").unlink()
    assert any("index is missing" in p for p in docs.check(root))


def test_wiki_has_home_grouped_sidebar_and_rewritten_links(tmp_path):
    root = sample(tmp_path)
    out = tmp_path / "wiki"
    count, missing = docs.build_wiki(root, out, "https://example.org/r", "main")
    assert count == 6 and missing == ["Facts", "Why"] or set(missing) <= {"Facts", "Why"}
    side = (out / "_Sidebar.md").read_text()
    assert side.index("**Tutorials**") < side.index("**How-to guides**") < side.index("**Explanation**") < side.index("**Reference**")
    assert "- [Learn](First-steps)" in side and "- [Do](Do-it)" in side
    assert (out / "Home.md").exists()
    page = (out / "Do-it.md").read_text()
    assert "[why](Why)" in page and "(https://example.org/r/blob/main/src/x.py)" in page
    assert "Generated from [docs/how-to/do-it.md]" in page


def test_this_repositorys_docs_follow_the_standard():
    assert docs.check(ROOT) == []
