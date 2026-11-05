# Library Adoption

**Purpose:** Let a repository refer to a solution that another library's records define, and tell the adopted, the specialized and its own solutions apart, so no job is described twice.

Breadcrumb: [Top](../../../../../esoi/README.md) > [A Project's Records and Code as One Structure](../README.md) > Library Adoption

Part of [A Project's Records and Code as One Structure](../README.md)

## Library Adoption (`library-adoption`)

- Out of scope: Reading and writing the records themselves (Intent Registry); running the rules (Structure Check); drawing the pages (Readable Records); reusing the library's measured results, which is a metric building on its foundation (Consumer Check); deciding that two jobs are the same, which a person does.
- Delegates to: intent-registry, structure-check, readable-records, consumer-check
- Entry call: `esoi.run("library-adoption", '.')`
- Selected implementation: Reference column (`reference-column`)
- Metric: Adoption clarity
- Implemented by: [`implementations/python/esoi/structure/library_adoption/interface.py`](interface.py), [`implementations/python/esoi/structure/library_adoption/resolve.py`](resolve.py), [`implementations/python/esoi/structure/structure_check/rules/adoption_rules.py`](../structure_check/rules/adoption_rules.py), [`implementations/python/esoi/understanding/readable_records/readme_adopted.py`](../../understanding/readable_records/readme_adopted.py)

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Reference column | `library-adoption:reference-column` | Two technical columns of solutions.csv, adopts and specializes, hold @library/solution_id, and the configuration's [adopts.<library>] names the library's repository; the registry keeps adopted rows apart, and the rule S53 resolves them. | [`implementations/python/esoi/structure/library_adoption/interface.py`](interface.py) | selected |
| Copied records | `library-adoption:copied-records` | The application copies the library's solution records and edits them, with a note of where each came from. | no code yet |  |

## Metrics

- Adoption clarity (`metric-adoption-clarity`)

## Problems

- Copies of a library's solutions in an application (`prob-copied-library-solutions`): An application that needs jobs a shared library already defines tends to copy the library's solution records into its own.

## Ideals

- An application's records say only what is its own (`ideal-own-records-only`): An application's records describe what only the application has, and a reader sees at once which jobs it borrows from a library and which it defines.

## Where to go next

- Up: [implementations/python/esoi](../../README.md)
- Intent: [A Project's Records and Code as One Structure](../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
