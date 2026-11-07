"""Solution coherence, paragraph check (M1, rule S38): the solution_coherence paragraph of an intent names every solution, states every uses edge in one clause with words of its own, and claims no relation the records do not hold."""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Tuple

MIN_CLAUSE_WORDS = 3          # words between the user and the used, names aside ("a uses b" has one: not enough)
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")


SOLUTION_NAMES: Dict[str, str] = {}   # {solution id: display name} of the repository being checked (set by ``check``), so a name inside a longer name is read as the longer one


def phrase(name: str) -> "re.Pattern":
    """A display name as a whole phrase: case-insensitive, any run of spaces, not inside a longer word."""
    return re.compile(r"(?<![\w-])" + r"\s+".join(re.escape(word) for word in name.split()) + r"(?![\w-])", re.IGNORECASE)


def position(sid: str, row: Dict[str, str], text: str) -> int:
    """Where ``text`` first names the solution, by id or by display name (a whole phrase, ignoring case and spacing), or -1. A name that
    only appears inside the longer name of another solution (``Mind`` inside ``Mind and body``) does not name this one."""
    found = re.search(r"(?<![\w@/-])" + re.escape(sid) + r"(?![\w-])", text)
    best = found.start() if found else -1
    name = " ".join((row.get("name") or "").split())
    if name:
        masked = text
        for other, longer in SOLUTION_NAMES.items():
            longer = " ".join(longer.split())
            if other != sid and len(longer) > len(name) and name.lower() in longer.lower():
                masked = phrase(longer).sub(lambda hit: " " * len(hit.group(0)), masked)
        hit = phrase(name).search(masked)
        if hit and (best < 0 or hit.start() < best):
            best = hit.start()
    return best


def sentences(text: str) -> List[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def clauses(text: str) -> List[str]:
    return [c for c in re.split(r"(?<=[.;:!?])\s+", text.strip()) if c]


def other_words(clause: str, names: List[str]) -> int:
    """Words of a clause that are not part of a solution id or name it contains."""
    rest = clause
    for n in sorted(names, key=len, reverse=True):
        rest = re.sub(re.escape(n), " ", rest, flags=re.IGNORECASE)
    return len(WORD.findall(rest))


def reaches(uses: Dict[str, List[str]], start: str, goal: str) -> bool:
    seen, stack = set(), [start]
    while stack:
        x = stack.pop()
        for t in uses.get(x, ()):
            if t == goal:
                return True
            if t not in seen:
                seen.add(t)
                stack.append(t)
    return False


def named_in(text: str, every_solution: Dict[str, Dict[str, str]], candidates) -> List[Tuple[int, str]]:
    """(position, id) of each candidate solution that ``text`` names, in the order they appear."""
    return sorted((position(sid, every_solution[sid], text), sid) for sid in candidates
                  if position(sid, every_solution[sid], text) >= 0)


def clause_subjects(parts: List[str], every_solution: Dict[str, Dict[str, str]], candidates) -> List[str]:
    """The solution each clause speaks of: the first it names; a clause opening with "It" keeps the subject of the clause before it."""
    subjects: List[str] = []
    for i, c in enumerate(parts):
        if re.match(r"^\s*It\b", c) and i and subjects[i - 1]:
            subjects.append(subjects[i - 1])
        else:
            named_at = named_in(c, every_solution, candidates)
            subjects.append(named_at[0][1] if named_at else "")
    return subjects


def naming_problems(para: str, mine: List[str], every_solution, uses, host_sid: str, host_uses, max_names: int) -> List[str]:
    """Problems with which solutions the paragraph names: several paragraphs, solutions missing, solutions of other intents, crowded sentences."""
    found: List[str] = []
    if re.search(r"\n\s*\n", para):
        found.append("more than one paragraph")
    missing = [s for s in mine if position(s, every_solution[s], para) < 0]
    if missing:
        found.append(f"names {len(mine) - len(missing)} of {len(mine)} solutions; missing: {', '.join(missing)}")
    allowed = set(mine) | {b for a in mine for b in uses[a]} | host_uses | {host_sid} | {
        s for s in every_solution if any(h in mine for h in uses[s])}
    stray = [s for s in every_solution if s not in allowed and position(s, every_solution[s], para) >= 0]
    if stray:
        found.append(f"names solutions of other intents no edge reaches: {', '.join(stray)}")
    crowded = []
    for s in sentences(para):
        n = len(named_in(s, every_solution, every_solution))
        if n > max_names:
            crowded.append(f"{n} in \"{s[:60]}...\"")
    if crowded:
        found.append(f"sentences naming more than {max_names} solutions: {'; '.join(crowded)}")
    return found


def stated_edges(parts: List[str], inner, mine: List[str], every_solution) -> Dict[str, str]:
    """The clause that states each uses edge: the user first, then the used, with words of their own between them."""
    stated: Dict[str, str] = {}
    subject = clause_subjects(parts, every_solution, mine)
    for a, b in sorted(inner):
        for i, c in enumerate(parts):
            pa, pb = position(a, every_solution[a], c), position(b, every_solution[b], c)
            if pa < 0 and re.match(r"^\s*It\b", c) and subject[i] == a:
                pa = 0
            if 0 <= pa < pb or (pa == 0 and pb > 0):
                names = [x for x in (a, b, every_solution[a].get("name", ""), every_solution[b].get("name", "")) if x]
                named_here = [sid for sid in every_solution if position(sid, every_solution[sid], c) >= 0]
                named_here += [every_solution[sid].get("name", "") for sid in named_here if every_solution[sid].get("name", "")]
                if other_words(c[max(pa, 0):pb], names + named_here) >= MIN_CLAUSE_WORDS:   # the words that join them
                    stated[f"{a}->{b}"] = c
                    break
    return stated


def templated_problem(stated: Dict[str, str], every_solution) -> List[str]:
    """A problem when four or more clauses state edges and over half of them share one wording once the names are taken out."""
    def skeleton(c: str) -> tuple:
        names = sorted([x for sid in every_solution if position(sid, every_solution[sid], c) >= 0
                        for x in (sid, every_solution[sid].get("name", "")) if x], key=len, reverse=True)
        return tuple(w.lower() for w in WORD.findall(re.sub("|".join(re.escape(x) for x in names) or "$^", " ", c)))
    distinct = set(stated.values())
    skeletons = Counter(skeleton(c) for c in distinct)
    if len(distinct) >= 4 and skeletons and skeletons.most_common(1)[0][1] * 2 > len(distinct):
        top = skeletons.most_common(1)[0]
        return [f"templated: {top[1]} of {len(distinct)} clauses that state edges share the words {' '.join(top[0])!r}"]
    return []


def clause_claims(c: str, first: str, start: int, named_at: List[Tuple[int, str]], every_solution, walk) -> List[str]:
    """The relations one clause states from ``first`` (named at ``start``) to a later solution that no uses path joins."""
    claimed = []
    present = {other for _, other in named_at}
    named_here = [x for other in every_solution if other in present for x in (other, every_solution[other].get("name", "")) if x]
    for at, sid in named_at:
        if sid == first or at <= start:
            continue
        names = [x for x in (first, sid, every_solution[first].get("name", ""), every_solution[sid].get("name", "")) if x]
        if other_words(c[max(start, 0):at], names + named_here) >= MIN_CLAUSE_WORDS and not reaches(walk, first, sid):
            claimed.append(f"{first}->{sid} in \"{c[:80]}\"")
    return claimed


def claimed_problem(parts: List[str], every_solution, uses, host_sid: str, host_uses) -> List[str]:
    """A problem for each relation the paragraph states between two solutions that no uses path of the records joins."""
    subject_any = clause_subjects(parts, every_solution, every_solution)
    walk = {s: list(t) for s, t in uses.items()}
    if host_sid:
        walk.setdefault(host_sid, []).extend(host_uses)
    claimed = []
    for i, c in enumerate(parts):
        named_at = named_in(c, every_solution, every_solution)
        if re.match(r"^\s*It\b", c) and i and subject_any[i - 1]:
            claimed += clause_claims(c, subject_any[i - 1], 0, named_at, every_solution, walk)
        elif named_at:
            claimed += clause_claims(c, named_at[0][1], named_at[0][0], named_at, every_solution, walk)
    if not claimed:
        return []
    return ["states a relation the records do not hold (no uses path from the first to the second): " + "; ".join(dict.fromkeys(claimed))]


def check_paragraph(para: str, problems, mine, every_solution, uses, host_sid, host_uses, inner, max_names) -> None:
    """Append to ``problems["paragraph"]`` every way ``para`` fails to state the intent's solutions and uses edges."""
    found = problems["paragraph"]
    if not para:
        found.append("solution_coherence is empty")
        return
    found += naming_problems(para, mine, every_solution, uses, host_sid, host_uses, max_names)
    parts = clauses(para)
    stated = stated_edges(parts, inner, mine, every_solution)
    found += templated_problem(stated, every_solution)
    found += claimed_problem(parts, every_solution, uses, host_sid, host_uses)
    unstated = sorted(f"{a}->{b}" for a, b in inner if f"{a}->{b}" not in stated)
    if unstated:
        found.append("uses edges not stated user first in one clause with words of its own: " + ", ".join(unstated))
