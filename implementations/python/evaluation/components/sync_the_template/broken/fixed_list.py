"""BASELINE: a hand-kept field list. It returns the fields as they were when someone last copied them and never
reads the text, so it cannot follow a refinement, a new field, an unfinished section or a missing section."""

FIELDS = {
    "problem": {"required": ["problem", "who_has_it", "why_it_matters", "why_hard", "existing_attempts"], "interface": []},
    "solution": {"required": ["name", "scoped_purpose", "goals", "knowledge", "measures_of_success"],
                 "interface": ["parameters", "inputs", "outputs", "effects", "usage_notes"]},
    "implementation": {"required": ["name", "description", "advantages", "disadvantages"], "interface": []},
    "ideal": {"required": ["name", "principle", "state_description", "hints_of_measurement"], "interface": []},
    "metric": {"required": ["name", "scoped_purpose", "record"], "interface": []},
}


def build(meter):
    def read(kind, args):
        if kind == "parse":
            return {"keys": FIELDS, "text": ""}
        return {"stale": False}
    return read
