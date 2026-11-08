"""CURRENT: the lexical hits plus the solutions their records link to, over this repository's own records. Zero model calls."""
from pathlib import Path

from esoi.understanding.solution_relevance import relevance_cases

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "esoi.toml").is_file())


def build(meter):
    return relevance_cases.runner(ROOT, "index-with-links")
