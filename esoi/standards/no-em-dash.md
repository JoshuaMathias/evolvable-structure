# No em dashes

**Read when:** Writing docs, records, code comments or messages in this repository.

**Problem it prevents:** Em dashes in text, which this repository's voice rule forbids.

**Tags:** public-text, low-quality-code
**Paths:** docs/**/*.md; esoi/**/*.csv; implementations/python/**/*.py
**Rule:** Write two sentences, a comma, a colon or parentheses where an em dash would go.
**Check:** regex:\u2014 => Em dash. Use two sentences, a comma, a colon or parentheses.
