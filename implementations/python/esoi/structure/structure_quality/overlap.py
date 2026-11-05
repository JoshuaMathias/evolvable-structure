"""The word-overlap measure of two texts: the one measure rule S48 (siblings that say the same job), rule S53 (an own solution that repeats a library
solution) and Structure Quality (do the arms of one solution share one purpose) all read, so it is written once.

It compares the content words of two texts (the words of four or more letters that are not filler). It finds candidates for a person to read;
it is not a verdict that two roles are the same.
"""
from __future__ import annotations

import re
from typing import Iterable

STOP = frozenset("that this with from into their they them have has been being each every which what when where while than then also only "
                 "such more most other over under about between without within through whose these those will would could should can may might "
                 "does done make makes made using used uses use its itself your you our are for the and not but any all one two".split())
OVERLAP = 0.45          # shared share of the content words of two sibling solutions that is called strong overlap
OVERLAP_WORDS = 6       # and at least this many shared words, so two short texts do not match by accident
ARMS_SHARE_LITTLE = 0.06   # a mean pairwise overlap of the arms of one solution below this is a prompt to read them for one purpose


def content(text: str) -> frozenset:
    return frozenset(w for w in re.findall(r"[a-z][a-z-]{3,}", (text or "").lower()) if w not in STOP)


def mean_overlap(texts: Iterable[str]) -> float:
    """The mean, over every pair of texts that have content words, of shared words divided by all words; 1.0 when there is no pair."""
    words = [content(t) for t in texts]
    pairs = [(a & b, a | b) for n, a in enumerate(words) for b in words[n + 1:] if a and b]
    return sum(len(s) / len(u) for s, u in pairs) / len(pairs) if pairs else 1.0
