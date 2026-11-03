# Names

**Read when:** Naming a function, class or module-level value in the Python package.

**Problem it prevents:** Underscore-prefixed names that hide shared code from the next author and from tests.

**Tags:** naming, low-quality-code
**Paths:** implementations/python/**/*.py
**Rule:** Give functions and classes plain descriptive names with no leading underscore; dunders are the only exception.
**Check:** regex:^\s*(async\s+)?(def|class)\s+_(?!_) => Underscore-prefixed name. Give it a plain, descriptive name (dunders are fine).
