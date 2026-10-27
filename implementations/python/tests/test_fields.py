"""Tags with their risk ids, and the mechanical migration of the scoped_purpose records."""
import pytest

from esoi import fields, tables


def test_tags_round_trip_and_read_the_older_form():
    tags = [{"tag": "dedup", "risk_ids": ["R1", "prob-x"]}, {"tag": "python", "risk_ids": []}]
    assert fields.parse_tags(fields.format_tags(tags)) == tags
    assert fields.parse_tags("") == [] and fields.format_tags([]) == ""
    assert fields.parse_tags("a; b") == [{"tag": "a", "risk_ids": []}, {"tag": "b", "risk_ids": []}]
    with pytest.raises(ValueError):
        fields.parse_tags('{"tag": "x"}')


def test_solution_text_splits_by_whole_sentences():
    old = "Use for choosing which implementation serves a solution. Avoids deciding which one is best (the leaderboard does)."
    assert fields.split_solution_text(old) == ("Use for choosing which implementation serves a solution.",
                                               "Avoids deciding which one is best (the leaderboard does).")
    assert fields.split_solution_text("Greet one person. It does not translate.") == ("Greet one person.", "It does not translate.")


def test_metric_text_moves_only_a_blind_spot_sentence():
    assert fields.split_metric_text("Measures the form. It cannot see tone.") == ("Measures the form.", "It cannot see tone.")
    assert fields.split_metric_text("Measures the form.") == ("Measures the form.", "")


def test_old_rows_load_in_the_new_fields():
    sol = fields.upgrade_row("solution", {"solution_id": "s", "scoped_purpose": "Do it. Avoids more.", "risk_addressed": "R1", "tags": "x"})
    assert sol["purpose"] == "Do it." and sol["out_of_scope"] == "Avoids more." and "scoped_purpose" not in sol
    assert fields.parse_tags(sol["tags"]) == [{"tag": "x", "risk_ids": ["R1"]}]
    met = fields.upgrade_row("metric", {"metric_id": "m", "scoped_purpose": "Counts."})
    assert met["purpose"] == "Counts." and met["disadvantages"] == ""
    current = {"solution_id": "s", "purpose": "Do it."}
    assert fields.upgrade_row("solution", current) is current


def test_migrate_folder_rewrites_in_place(tmp_path):
    tables.write_csv(tmp_path / "solutions.csv", ["solution_id", "name", "scoped_purpose", "milestones", "risk_addressed"],
                     [{"solution_id": "s", "name": "S", "scoped_purpose": "Do it. It avoids more.", "milestones": "1. x"}])
    tables.write_csv(tmp_path / "metrics.csv", ["metric_id", "name", "scoped_purpose", "record"],
                     [{"metric_id": "m", "name": "M", "scoped_purpose": "Counts.", "record": "n"}])
    assert len(fields.migrate_folder(tmp_path, apply=False)) == 2
    assert "scoped_purpose" in tables.read_header(tmp_path / "solutions.csv")
    assert len(fields.migrate_folder(tmp_path)) == 2
    assert tables.read_header(tmp_path / "solutions.csv") == ["solution_id", "name", "description", "purpose", "approach",
                                                              "out_of_scope", "milestones", "tags"]
    assert tables.read_header(tmp_path / "metrics.csv") == ["metric_id", "name", "purpose", "record", "disadvantages"]
    assert tables.read_csv(tmp_path / "solutions.csv")[0]["out_of_scope"] == "It avoids more."
    assert fields.migrate_folder(tmp_path) == []
