"""The ESOI behaviour function. Every implementation is ONE function with this signature:

    respond(case: dict) -> str

``case["scenario"]`` is the message a person sends an AI agent; the function returns the agent's reply and must use only
``scenario`` (every other column is the answer key). The scorer then checks the reply against the case's ``must_have``
regexes (all must match) and ``must_not`` regexes (none may match), case-insensitively. An arm whose function carries a
``judge`` attribute is graded by that model judge instead, with the regexes as a prefilter (see ``esoi.behaviour``).

What this measures: whether an AI agent acts by the evolvable-structure principles in its own work, one primary principle
per case (``P1`` to ``P13``; ``P0`` is the skill's own purpose and instructions), including cases where adding structure is
the wrong answer and cases whose point is to keep a qualifier. ``cases.csv`` is one row per scenario, built to be reviewed
as a sheet: the ``reviewer_*`` columns are the human's.

Offline validity (no model, no cost): ``reference_good`` returns each case's ``good_reference`` and must pass every case;
``reference_bad`` returns ``bad_reference`` and must fail every case. That proves the checks tell acting by the principles
from not acting by them. The arms that call a model (the skill as standing instructions, the skill on request, and no
skill) declare ``PAID = True`` and are run only when Joshua has approved the spend.
"""
