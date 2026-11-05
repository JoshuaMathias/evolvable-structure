"""Generate this repository's GitHub wiki from docs/: a thin wrapper over `esoi docs wiki` (the code lives in esoi/understanding/the_standard/docs.py).

    python scripts/docs_to_wiki.py --out <wiki checkout> [--check]

Writes the pages only; pushing the wiki is a separate, explicit step (`esoi docs wiki ... --push <wiki git url>`).
"""
import sys

from esoi.__main__ import main

if __name__ == "__main__":
    sys.exit(main(["docs", "wiki", "--extra", "skill/evolvable-structure/steps.md", *sys.argv[1:]]))
