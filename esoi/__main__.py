"""``python -m esoi`` is the same as the ``esoi`` command."""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
