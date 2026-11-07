"""The navigable-records fixture leaves no laid-out tree in the temporary folder once its process ends."""
import glob
import subprocess
import sys
import os
from pathlib import Path

COMPONENTS = Path(__file__).resolve().parents[1] / "evaluation" / "components"
SCRIPT = (
    "import sys\n"
    f"sys.path.insert(0, {str(COMPONENTS)!r})\n"
    "from shared_fixtures import navigable_fixture\n"
    "navigable_fixture.layout('this', 'beside_code')\n"
    "navigable_fixture.layout('this', 'beside_code', True)\n"
)


def test_no_laid_out_tree_remains_after_the_process_exits(tmp_path):
    env = dict(os.environ, TMPDIR=str(tmp_path))
    subprocess.run([sys.executable, "-c", SCRIPT], check=True, env=env)
    assert glob.glob(str(tmp_path / "navigable-*")) == []
