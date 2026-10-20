# A metric must be meaningfully real

A metric turns something qualitative or conceptual into a number so that alternatives can be compared. It may do that
creatively, in an unusual or limited way: a rubric scored by a judge, a labelled set of requests, a count of steps a newcomer
needed, a proxy for taste. What it may not do is measure a stand-in. **Every metric must measure real behaviour, on real
inputs, producing real outputs, judged by the real thing it claims to judge.** A number from a scripted judge, a mocked model, a
canned answer or a hand-typed value measures the plumbing around the thing, and a decision that rests on it is not backed by
evidence (the problem `prob-simulated-arm-false-loss` is one way this goes wrong; a perfect scripted judge scoring 100% is
another).

## What real means

- **The judged thing is the real thing.** If a metric says a model picks the right record, a model picks it. If it says a search
  finds the right file, the search that ships runs over the files that ship.
- **The inputs are labelled and can lose.** A case set where the baseline passes almost everything cannot tell the alternatives
  apart. Include cases only the better alternative handles (other words for the same need, noisy requests, requests that
  concern nothing) and keep the `broken/` baselines for invariants.
- **Limited is fine, fake is not.** A small labelled set, a single cheap judge model or a proxy score is a limited measure, and
  the metric's record should say what it does and does not cover. A scripted stand-in is not a limited measure of the thing;
  it is a measure of something else.
- **Plumbing still gets tested.** A scripted judge is the right tool for a unit test of batching, retries or error handling.
  Keep it in the tests, not in the metric.
- **Cost and noise are part of the record.** A real run costs tokens and moves a little between repeats; the results log
  records both, and a small margin between two real runs is noise.

## What `esoi check` does about it (S31)

- An implementation in a metric's evaluation folder that declares `SIMULATED = True` is a finding: the number it records is
  the number of a stand-in.
- A metric record whose purpose or record field describes its judge or model as scripted, simulated, mocked, stubbed, fake or
  canned, or as a stand-in, is a finding.

The way out is to make the metric real. Where a metric truly cannot be (a paid service with no test mode, a human who is not
available), add a waiver naming the metric and why; the waiver is the visible, reviewable admission that the number is not
yet backed by the real thing. The lint can only see what a record or an arm admits, so reviewing a metric's cases for this is
still a human and AI judgement: ask of every new metric, "if the alternative were actually worse, would this number show it?"
