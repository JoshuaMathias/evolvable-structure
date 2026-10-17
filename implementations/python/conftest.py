"""Makes the package importable when the tests and evaluations run from a checkout without installing it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
