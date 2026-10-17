"""The ESOI behaviour judge. Every implementation is ONE function with this signature:

    grade(case: dict) -> {"verdict": "pass" | "fail", "reason": str}

``case["case_id"]`` names a case in ``behave_by_esoi/cases.csv`` and ``case["side"]`` says which of its two recorded replies
to grade (``good`` is the ``good_reference``, ``bad`` the ``bad_reference``). The function receives the case already joined to
that reply as ``case["reply"]`` and the behaviour case as ``case["behavior_case"]``.

The label is the answer key: ``human_verdict`` when a person has filled it in, else ``expected`` (pass for a good reply, fail
for a bad one, which is the case author's own label). What this measures is how often a judge agrees with those labels. It is
the judge's own metric, separate from the behaviour scores the judge is used for. While the labels are the author's, agreement
shows the judge is not broken, not that it is right; calibration needs a person's verdicts in ``human_verdict``.
"""
