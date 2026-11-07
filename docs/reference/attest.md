# `esoi attest`: a result that still holds after a change to the arm

A result goes stale when the arm's **own code** changes ([when a result is stale](../how-to/choose-when-a-result-is-stale.md)). Some
changes cannot move the number: a rename, a comment, a refactor that keeps behaviour. A person says so with an attestation, and the
result counts as current for that range of commits.

```
esoi attest <component> <impl> --reason "renamed two locals; behaviour unchanged" [--through SHA] [--author "Name <mail>"]
```

## What it records

One row of `attestations.csv`, beside the results log (`<evaluation>/attestations.csv`; commit it with the change it covers):

| Column | Meaning |
|---|---|
| `date`, `author` | when, and who (default `git config user.name` and `user.email`) |
| `component`, `impl` | the arm |
| `from_sha`, `through_sha` | the commit range: from the commit the result was recorded at (or where the arm's previous attestation ended) through `--through` (default `HEAD`) |
| `reason` | required text |
| `files` | the own-code files that changed in the range |

## What counts as current, and when it stops

The row is judged against `through_sha` instead of the commit it was recorded at, so the changes inside the range no longer make it
stale. Any later change to the arm's own code (a later commit, or an uncommitted edit) makes it stale again; attest again, which
chains from where the last one ended, or re-run the arm. `esoi leaderboard` shows `= <impl>: current by attestation (<reason>)`.

## What it refuses

| Refused | Why |
|---|---|
| no `--reason`, or an empty one | an attestation without a reason says nothing |
| no whole-run result for the arm | nothing to attest |
| the result was recorded on uncommitted code, or with no commit | there is no commit range |
| nothing in the arm's own code changed | the result is already current |
| the arm's own code changed outside the range (an uncommitted edit, or a commit after `--through`) | the attestation would hide a change nobody looked at: commit it and attest through it, or re-run |

Only a person can know a change kept the measurement, so the command never guesses: it checks the range and records the claim.

## Staleness informs

Stale or attested, a row only informs. It does not fail `esoi check` and is not a to do there (one information line counts the stale rows), does not start a re-run (`esoi run --stale` re-runs only what is
worth running and says why), and `esoi leaderboard` ranks every row it holds. The one place a stale row is set aside is promotion
(`esoi select --promote` counts only current results, so a verdict never rests on a result of other code); an attestation, like a
re-run, is how an arm whose code changed counts again.
