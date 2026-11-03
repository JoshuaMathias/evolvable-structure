# Glossary

esoi uses its own words for familiar ideas. Each has a conventional name; this page pairs them. The conventional word comes first.

| Conventional word | ESOI word | Meaning |
|---|---|---|
| Interface | solution | A narrow contract for one job, written as a `typing.Protocol`. |
| Implementation, backend, provider | arm | A concrete class that fills an interface. |
| Configured variant | `arm@option=value` | An implementation with one setting changed, scored as its own row. |
| Eval, scorer | metric | A check that gives each implementation a result on shared cases. |
| Eval results table | leaderboard | The recorded results of every implementation on every check. |
| Default, promote to default | selected, promote | The implementation a call builds when you pass nothing, set from the metric. |
| Staged evals (smoke, sample, full) | cascade, stages | Cheap evals first, costlier ones only for implementations that pass. |
| Lockfile | lock | A file (`esoi.lock.json`) that pins the defaults so production changes when you decide. |
| Dependency injection override | `provided=` | You pass your own object for an interface instead of the default. |
| Missing-configuration error | `Pending` | Raised when a call cannot run yet; the message names the key or install. |
| The project's goal | intent, top intent | The aim the whole project serves. |
| Requirement, design goal | problem, ideal | What goes wrong without a part, and what good looks like. |
| Composite component | area, composition arm | A component that calls its parts, each reached through its own interface. |
| Function, scorer or repository | kind (event, evaluate, store) | What a call returns: an output for an input (event), a score or feedback on the artifact passed in (evaluate), or a ready handle to query (store). |
| Sub-project | sub-intent | A smaller goal inside the project's goal. |
| Architecture overview kept in step with the code | solution coherence | One paragraph per project saying how its parts fit together; a check holds each stated relation to the recorded dependencies and the code. |
| Lint suppression with a reason | waiver | A recorded exception to a check, with why. |
