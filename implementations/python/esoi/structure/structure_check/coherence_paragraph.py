"""Solution coherence, paragraph check (M1, rule S38): the solution_coherence paragraph of an intent names every solution, states every uses edge in one clause with words of its own, and claims no relation the records do not hold."""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List

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


def check_paragraph(para: str, problems, mine, every_solution, uses, host_sid, host_uses, inner, max_names) -> None:
    """Append to ``problems["paragraph"]`` every way ``para`` fails to state the intent's solutions and uses edges."""
    stated: Dict[str, str] = {}
    if not para:
        problems["paragraph"].append("solution_coherence is empty")
    else:
        if re.search(r"\n\s*\n", para):
            problems["paragraph"].append("more than one paragraph")
        missing = [s for s in mine if position(s, every_solution[s], para) < 0]
        if missing:
            problems["paragraph"].append(f"names {len(mine) - len(missing)} of {len(mine)} solutions; missing: {', '.join(missing)}")
        allowed = set(mine) | {b for a in mine for b in uses[a]} | host_uses | {host_sid} | {
            s for s in every_solution if any(h in mine for h in uses[s])}
        stray = [s for s in every_solution if s not in allowed and position(s, every_solution[s], para) >= 0]
        if stray:
            problems["paragraph"].append(f"names solutions of other intents no edge reaches: {', '.join(stray)}")
        crowded = []
        for s in sentences(para):
            n = sum(1 for sid in every_solution if position(sid, every_solution[sid], s) >= 0)
            if n > max_names:
                crowded.append(f"{n} in \"{s[:60]}...\"")
        if crowded:
            problems["paragraph"].append(f"sentences naming more than {max_names} solutions: {'; '.join(crowded)}")
        parts = clauses(para)
        subject: List[str] = []     # a clause opening with "It" speaks of the first solution the clause before it names
        for i, c in enumerate(parts):
            named_at = sorted((position(sid, every_solution[sid], c), sid) for sid in mine
                              if position(sid, every_solution[sid], c) >= 0)
            if re.match(r"^\s*It\b", c) and i and subject[i - 1]:
                subject.append(subject[i - 1])
            else:
                subject.append(named_at[0][1] if named_at else "")
        subject_any: List[str] = []
        for i, c in enumerate(parts):
            every_named = sorted((position(sid, every_solution[sid], c), sid) for sid in every_solution
                                 if position(sid, every_solution[sid], c) >= 0)
            subject_any.append(subject_any[i - 1] if re.match(r"^\s*It\b", c) and i and subject_any[i - 1]
                               else (every_named[0][1] if every_named else ""))
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
        skeletons = Counter(tuple(w.lower() for w in WORD.findall(re.sub("|".join(re.escape(x) for x in sorted(
            [x for sid in every_solution if position(sid, every_solution[sid], c) >= 0 for x in (sid, every_solution[sid].get("name", "")) if x], key=len, reverse=True)) or "$^", " ", c)))
            for c in set(stated.values()))
        if len(set(stated.values())) >= 4 and skeletons and skeletons.most_common(1)[0][1] * 2 > len(set(stated.values())):
            problems["paragraph"].append(f"templated: {skeletons.most_common(1)[0][1]} of {len(set(stated.values()))} clauses "
                                         f"that state edges share the words {' '.join(skeletons.most_common(1)[0][0])!r}")
        walk = {s: list(t) for s, t in uses.items()}
        if host_sid:
            walk.setdefault(host_sid, []).extend(host_uses)
        claimed = []
        for i, c in enumerate(parts):
            named_at = sorted((position(sid, every_solution[sid], c), sid) for sid in every_solution
                              if position(sid, every_solution[sid], c) >= 0)
            if re.match(r"^\s*It\b", c) and i and subject_any[i - 1]:
                first, start = subject_any[i - 1], 0
            elif named_at:
                start, first = named_at[0]
            else:
                continue
            for at, sid in named_at:
                if sid == first or at <= start:
                    continue
                names = [x for x in (first, sid, every_solution[first].get("name", ""), every_solution[sid].get("name", "")) if x]
                named_here = [x for other in every_solution if position(other, every_solution[other], c) >= 0 for x in (other, every_solution[other].get("name", "")) if x]
                if other_words(c[max(start, 0):at], names + named_here) >= MIN_CLAUSE_WORDS and not reaches(walk, first, sid):
                    claimed.append(f"{first}->{sid} in \"{c[:80]}\"")
        if claimed:
            problems["paragraph"].append("states a relation the records do not hold (no uses path from the first to the second): "
                                         + "; ".join(dict.fromkeys(claimed)))
        unstated = sorted(f"{a}->{b}" for a, b in inner if f"{a}->{b}" not in stated)
        if unstated:
            problems["paragraph"].append("uses edges not stated user first in one clause with words of its own: "
                                         + ", ".join(unstated))
