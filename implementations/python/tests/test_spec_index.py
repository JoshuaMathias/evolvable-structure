"""The specification index: entries, links, tiers, lexical narrowing, and the command line, over a scaffolded project."""
import json

import pytest

from esoi import cli, spec_index


def test_every_record_is_one_entry_with_its_own_id_and_two_way_links(cfg):
    index = spec_index.build(cfg)
    by_id = {e["id"]: e for e in index["entries"]}
    assert index["n"] == len(by_id) == len(index["entries"])
    assert {e["kind"] for e in index["entries"]} >= {"intent", "problem", "solution", "implementation", "ideal", "metric"}
    for entry in index["entries"]:
        for ref in entry["refs"]:
            assert entry["id"] in by_id[ref]["refs"], f"{entry['id']} links {ref} but not back"


def test_the_index_is_plain_json_and_its_digest_follows_the_records(cfg):
    first = spec_index.build(cfg)
    assert json.loads(json.dumps(first)) == first
    assert spec_index.build(cfg)["digest"] == first["digest"]
    path = cfg.structure / "problems.csv"
    path.write_text(path.read_text().replace("greet", "welcome", 1))
    assert spec_index.build(cfg)["digest"] != first["digest"]


def test_tiers_disclose_one_record_progressively(cfg):
    index = spec_index.build(cfg)
    entry = next(e for e in index["entries"] if e["kind"] == "solution")
    zero, one, two = (spec_index.show(cfg, index, entry["id"], t) for t in (0, 1, 2))
    assert zero.count("\n") == 0 and one.startswith(zero) and two.startswith(one)
    assert "solution_id:" in two and "solution_id:" not in one
    with pytest.raises(KeyError):
        spec_index.show(cfg, index, "no-such-record")


def test_find_ranks_by_rare_words_and_never_guesses(cfg):
    index = spec_index.build(cfg)
    entry = next(e for e in index["entries"] if e["kind"] == "solution")
    word = max(entry["terms"], key=lambda t: (index["df"][t] == 1, entry["terms"][t]))
    assert spec_index.find_specs(index, word, 3)[0]["id"] in {e["id"] for e in index["entries"] if word in e["terms"]}
    assert spec_index.find_specs(index, "zebra quokka marmalade", 5) == []


def test_expand_adds_linked_records_after_the_direct_hits(cfg):
    index = spec_index.build(cfg)
    entry = next(e for e in index["entries"] if e["kind"] == "solution" and e["refs"])
    hits = spec_index.find_specs(index, entry["id"].replace("-", " "), 1, 2)
    assert hits[0]["via"] == "" and all(h["via"] == hits[0]["id"] for h in hits[1:]) and len(hits) > 1


def test_the_command_line_finds_shows_and_writes_the_index(cfg, repo, tmp_path, capsys):
    out = tmp_path / "index.json"
    assert cli.main(["--config", str(repo), "spec", "index", "--out", str(out)]) == 0
    assert json.loads(out.read_text())["n"] > 0
    solution_id = next(e["id"] for e in json.loads(out.read_text())["entries"] if e["kind"] == "solution")
    assert cli.main(["--config", str(repo), "spec", "find", solution_id.replace("-", " ")]) == 0
    assert solution_id in capsys.readouterr().out
    assert cli.main(["--config", str(repo), "spec", "show", solution_id, "--tier", "2"]) == 0
    assert cli.main(["--config", str(repo), "spec", "show", "nope"]) == 1
    assert cli.main(["--config", str(repo), "spec", "find"]) == 2
