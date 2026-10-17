"""Small shared helpers: cells, globs, CSV round trips, file listing."""
from esoi import tables


def test_ids_splits_strips_and_drops_empties():
    assert tables.ids(" a ; b;;c ") == ["a", "b", "c"]
    assert tables.ids("") == []


def test_glob_star_stays_in_a_folder_and_double_star_crosses():
    assert tables.glob_re("a/*.py").match("a/x.py")
    assert not tables.glob_re("a/*.py").match("a/b/x.py")
    assert tables.glob_re("a/**").match("a/b/x.py")
    assert tables.glob_re("a/?.py").match("a/x.py")


def test_csv_round_trip_keeps_commas_quotes_and_newlines(tmp_path):
    rows = [{"a": "x, y", "b": 'say "hi"', "c": "line\nbreak"}]
    path = tmp_path / "t.csv"
    tables.write_csv(path, ["a", "b", "c"], rows)
    assert tables.read_csv(path) == rows
    assert tables.read_header(path) == ["a", "b", "c"]
    assert tables.read_csv(tmp_path / "missing.csv") == []


def test_repo_files_falls_back_to_a_walk_outside_git(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("x")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "c.pyc").write_text("x")
    assert tables.repo_files(tmp_path) == ["a.txt", "sub/b.txt"]


def test_a_csv_saved_with_a_byte_order_mark_still_has_its_first_column(tmp_path):
    path = tmp_path / "a.csv"
    path.write_bytes(b"\xef\xbb\xbfsolution_id,name\nx,y\n")
    assert tables.read_header(path) == ["solution_id", "name"] and tables.read_csv(path) == [{"solution_id": "x", "name": "y"}]
