"""BASELINE: the records kept by hand. The code is never read, so a declared alternative nobody recorded is not noticed,
nothing is written for it, and a new solution is only a folder name. Zero model calls."""


def build(meter):
    def specify(kind, args):
        if kind == "scan":
            return {"solutions": [], "implementations": [], "ports": {}, "parameters": {}, "outputs": {}}
        if kind == "sync":
            return {"before_count": 0, "after_count": 0, "changes": 0, "second": 0, "kept": True, "row": {}}
        return {"files": [], "text_only": True, "valid": True, "refused": False, "problems": []}
    return specify
