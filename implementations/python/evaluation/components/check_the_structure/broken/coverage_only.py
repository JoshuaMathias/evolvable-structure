"""BASELINE: a checker that only does file coverage (every file belongs to exactly one component, every glob matches
a file), the naive version a first draft would write. Zero model calls."""
from shared_fixtures.interface import coverage_only_checker

build = coverage_only_checker.build
