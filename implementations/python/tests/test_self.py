"""This repository's own structure: ESOI applied to itself, and the hygiene rules of a public repository."""
import re
import subprocess
from pathlib import Path

import pytest

from esoi import check, config, hygiene

REPO = Path(__file__).resolve().parents[3]
PACKAGE = REPO / "implementations" / "python"
pytestmark = pytest.mark.skipif(not (REPO / "esoi.toml").exists(), reason="not run from a checkout of the repository")


def tracked():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=REPO, capture_output=True, text=True)
    return [REPO / f for f in out.stdout.splitlines() if (REPO / f).is_file()]


def test_the_repository_follows_its_own_structure():
    assert check.check(config.load(REPO)) == []


def test_the_repository_is_clean_for_a_public_repo():
    assert hygiene.scan_repo(REPO, allow=hygiene.allowances_from(config.load(REPO).hygiene)) == []


def test_no_em_dashes_anywhere():
    bad = [str(p.relative_to(REPO)) for p in tracked() if chr(0x2014) in p.read_text(errors="ignore")]
    assert bad == []


def test_no_underscore_prefixed_names_in_the_python_implementation():
    pattern = re.compile(r"\b(?:def|class)\s+_[A-Za-z]\w*|(?<![\w.])_[a-z]\w*\s*=(?!=)|\bself\._[a-z]\w*|\b\w+\._[a-z]\w*\(")
    bad = []
    for path in PACKAGE.rglob("*.py"):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if pattern.search(line) and not line.lstrip().startswith("#"):
                bad.append(f"{path.relative_to(REPO)}:{number}: {line.strip()[:70]}")
    assert bad == []


def test_adopters_are_named_only_in_the_examples_and_the_rules_about_editing():
    allowed = {REPO / "CLAUDE.md", Path(__file__).resolve()}
    names = re.compile(r"\bqar\b|quest[-_ ]ai[-_ ]runner|quest[-_]backend|spiritual|\bQuest\b", re.I)
    bad = [str(p.relative_to(REPO)) for p in tracked()
           if (REPO / "examples") not in p.parents and (REPO / "skill") not in p.parents and PACKAGE / "esoi" / "data" / "skill" not in p.parents
           and p not in allowed and not p.name.endswith(".csv") and names.search(p.read_text(errors="ignore"))]
    assert bad == []
