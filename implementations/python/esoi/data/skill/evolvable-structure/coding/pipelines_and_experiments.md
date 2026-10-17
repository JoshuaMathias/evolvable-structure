# evolvable-structure coding examples: pipelines, data model and experiments

Part of `../coding.md`. A data-science pipeline library of Joshua's, built on a name-keyed registry. Load for pipeline stages, a data model and storage routing, environments, experiment workflows, or one function for many entry points. These are how one project met an ideal, not rules for every
project: carry over the purpose, and copy the mechanism only where the codebase already uses it.
Evidence pointers read `file > heading`, with files in `../sources/`.

**3. Pipeline library: pipeline stages declare inputs and outputs as data.** *Purpose:* a stage should run in
a pipeline or alone with no glue (pattern 8). A plain function is wrapped by a decorator that names its
input and output field paths; the decorator loads, stores, skips work already done, and has a
standalone mode for tests. A pipeline is then a list of names.

```python
@process_data(collection_name="feature_data", output_fields=['name', 'value', 'version_name'])
def train_prediction(...): ...
# run_entity_pipeline: for func in functions: entity = func(entity=entity, **kwargs)
```

**4. Pipeline library: the data model is addressed by a field-path grammar.** *Purpose:* a new field or
relationship should need no schema change (pattern 1). Field names are dot paths; the name decides the
storage (a file extension goes to object storage, `.json` marks a sub-dictionary), links are named in
the path, and an explicit argument overrides the convention.

**5. Pipeline library: routing and environments are one map and a few variables.** *Purpose:* each setting in
one place, and environments that differ by substitution, not by fork (pattern 4). Collection to database
sits in one dict, connection strings come from env vars, and CI for develop, qa and main is one
template with three substitutions.

**6. Pipeline library: experiments are thin wrappers around one shared trainer.** *Purpose:* alternatives that
can be compared (pattern 9). Module-level constants, an entry function with keyword defaults, and a call
to the shared trainer. Comparisons run on a dataset frozen once, a version is a run of a named function
with its parameters saved, and one version is the baseline.

**7. Pipeline library: one function, every entry point.** *Purpose:* experiment and production share one path
(pattern 8). The same function serves the notebook, the CLI (`fire.Fire(mod)`), the pipeline and the
test.

## Known weaknesses

The registry was copied into the library and drifted. Two entity converters are broken or stubbed, and `process_data` and `calculate_metrics` have bugs. Lesson: one shared copy, reached through the dependency line.
