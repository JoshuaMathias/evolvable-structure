# Judge public evidence like a scientist

Other people's evaluations of a model, a library or a tool say things a small private test cannot: how it behaves at scale, how
fast and costly it is on other people's workloads, whether it breaks. They are complementary to our own results. They are also
easy to over-read, so ESOI grades them on the evidence about the evidence, not on the size of the number.

## One eval is never enough

A single number can be a fluke, a quirk of one harness or a one-off. So one source is graded B at most, and A is reachable only
when two independent sources agree. A contradiction between sources is never averaged away: it lowers the grade, names both
rows, and says which single run of ours would decide.

## A vendor number is a claim

A vendor chose the benchmark, the settings and the run, and reports its own product. That is a claim to test, not a measurement.
A lone vendor number (or a maintainer's own benchmark page) is grade D and cannot place an arm above one that someone with no
stake measured. It stays visible, marked provisional, and the report says what one independent run would settle it.

## Saturated, archived and leaked benchmarks

When every candidate scores near the ceiling the benchmark no longer separates them, and a benchmark that may be in training data
measures memory. Both lose points and raise a flag that blocks use. A difference inside a dimension's tolerance is called "not a
real difference", not a win.

## Confounds and units

A difference in harness, prompt or tools looks like a difference in the model. A named confound lowers the grade and the report
says to run the candidates through one harness. A latency in seconds and a throughput in tokens per second are different
measures, and a price per token is not a price per task; units convert only through an explicit table and otherwise the numbers
are flagged and never compared.

## What it does not do

Public evidence is never a result row, never enters a leaderboard and never chooses an implementation by itself. Our own
measurement on our own cases remains the basis for selection. The grader compares the two: where the public ranking and ours
agree, confidence rises; where they conflict, that is information about our cases or about the benchmark, recorded, not
suppressed. The weights are in one visible table with a reason each (`esoi evidence table`), so a reviewer can disagree with a
weight rather than with a hidden judgement.

How: [Use public evidence beside your own results](../guides/use-public-evidence.md).
