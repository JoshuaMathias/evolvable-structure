"""The guide to keeping a metric before and after a piece of work: every python block of it is run, and what it prints is what it says."""
import re
from pathlib import Path

GUIDE = Path(__file__).resolve().parents[3] / "docs" / "guides" / "measure-before-and-after.md"


def test_every_python_block_of_the_guide_runs_and_prints_what_it_says(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    blocks = re.findall(r"```python\n(.*?)```", GUIDE.read_text(encoding="utf-8"), re.S)
    assert len(blocks) == 4
    namespace = {"__name__": "guide"}
    for block in blocks:
        exec(compile(block, str(GUIDE), "exec"), namespace)   # the guide's own examples, run as written
    claimed = re.findall(r"^print\(.*\)\n# (.+)$", "\n".join(blocks), re.M)
    assert len(claimed) == 3 and capsys.readouterr().out.splitlines() == claimed
    assert "NEXT PRIORITY" in namespace["brief"] and namespace["found"].solution_id == "greet-a-person"
    assert [r.source for r in namespace["done"].results] == ["measured", "recorded"]
    assert (namespace["root"] / "ledger").is_dir()
