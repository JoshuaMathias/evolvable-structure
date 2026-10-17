"""BASELINE: a checker that only does file coverage (every file belongs to exactly one component, every glob matches
a file), the naive version a first draft would write. Zero model calls."""
from check_the_structure.broken.coverage_only import build  # noqa: F401
