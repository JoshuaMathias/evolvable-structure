# evolvable-structure coding examples: versioned components (Writealyze)

Part of `../coding.md`. Writealyze's design for reusable NLP components (atoms and molecules) and its notebooks (WriteABox, Atom, State of the Art NLP with 1 function). Load for versioning, swappable implementations, class contracts, or tuning against one metric. These are how one project met an ideal, not rules for every
project: carry over the purpose, and copy the mechanism only where the codebase already uses it.
Evidence pointers read `file > heading`, with files in `../sources/`.

**9. Writealyze design: atoms and molecules.** *Purpose:* improve a part without moving its callers,
and reuse it elsewhere (patterns 2 and 15). An atom is a reusable, versioned component referenced by
name; a molecule is the slot for a task whose current implementation is the best atom by a metric that
is itself swappable, so callers do not change when the winner does. The latest version is the default
and a user can pin one. This is mostly design: the notebooks (examples 13 and 14) are the built form,
and a registry library of his documents a `version` parameter it never built. McIlroy's 1968 component families,
whose members are chosen by early-bound parameters, are the same idea in older form.
Source: `components_research.md > McIlroy, 1968`.

```python
@writeatom(version='fast')
def preprocess_text(text):
    normalized = normalize_text(text)
    tokenized = tokenize_text(normalized, version='spacy')   # version is one argument
    return tokenized
```

**13. Writealyze WriteABox notebook: a box is one class contract.** *Purpose:* operations that swap
without new glue (pattern 13). The same class goes in and comes out: keyword arguments become parameters,
an optional `call` hook holds the one operation, a pipeline chains boxes, and unit tests pin the
contract. Swapping an operation is swapping a box.

**14. Writealyze Atom notebook: identity is kind and variant, and version is separate.** *Purpose:* an
updated part still fits its slot (patterns 2 and 14). Protons are the kind, neutrons the variant,
electrons the version, and equality and hash use only kind and variant.

```python
def __eq__(self, other):
    """ Equality of an atom (same type of Atom) is defined by protons and neutrons """
    return self.protons == other.protons and self.neutrons == other.neutrons
```

**15. Writealyze NLP notebook: one scorer name, and a tuner over any parameter dict.** *Purpose:* swap
the model behind a stable name and tune against one measure (patterns 2, 4 and 9). In "State of the Art
NLP with 1 function", `calculate_language_probability` keeps its name and docstring while the model
changes, every tuned constant is a keyword default measured from a corpus, and a tuner searches a
parameter dict against one fixed pairwise metric, calling
`calculate_language_probability(sentence, **parameter_weights)`.

## Known weaknesses

The notebooks have unfinished cells, a model cache that ignores the model name, declared but unused parameters, and a tuner that never backs off. Much of the atoms design is ideas, not built code.
