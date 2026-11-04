# Iterate on an LLM arm without repeating model calls

When you improve an arm that calls a model, most of what you change (parsing, scoring, a later step, one prompt out of five) leaves
most prompts the same, yet every run calls the model again for all of them. A cassette records each model call the meter wraps and
answers an identical call from the file. It is off unless you ask for it.

## Turn it on

```bash
esoi run <component> --impl <arm> --max-calls 40 --cassette evaluation/cassettes/<component>      # record misses, replay hits
esoi run <component> --impl <arm> --cassette evaluation/cassettes/<component> --cassette-only      # no new call allowed
esoi cassette stats evaluation/cassettes/<component>                                               # entries, hits, misses, size
```

Or once for the repository, in `esoi.toml` (a relative path is from the repository root):

```toml
[harness]
cassette = "evaluation/cassettes"
```

`--cassette DIR` overrides the setting. `esoi cassette stats` with no folder reads the setting.

## What is keyed and stored

The arm wraps its provider as before (`meter.wrap(provider, ("answer",))`). With a cassette on, every wrapped call gets a key, the
sha256 of the model, the method and its arguments (system, messages and every parameter that can change the answer; `timeout`,
`request_id`, `metadata` and `user` are left out). A call whose arguments have no JSON form has no stable key: it is made, counted
and not recorded.

- A hit returns the stored response and calls nothing. The meter counts it as replayed (`calls_replayed`), and the tokens, dollars
  and seconds the call originally cost are reported as the replayed cost, apart from the spend. The recorded row's `model_calls`,
  tokens and cost are only the new calls, and its `details` say how many calls were replayed and what they had cost.
- A miss calls the provider and records the response with its usage as one JSON line in `calls.jsonl`. A provider error is not
  recorded, so the next run tries again.
- The file is plain JSONL, safe to diff and review. It holds the key, method, model, response and usage, never the request text or any
  key or credential. A response that does not survive a JSON round trip is not recorded.
- `counts.json` beside it holds the hit and miss counters that `esoi cassette stats` prints; it is safe to leave out of version control.

Whether to commit the cassette is the repository's choice. A response it holds may be as sensitive as the prompts and the data
that produced it.

## Offline runs and `--cassette-only`

- An offline run (an arm not declared `PAID = True`, with no `--max-calls`) still may not call a model. A cassette hit in it is
  allowed, because no process starts; a miss is refused and counted among the attempted calls.
- `--cassette-only` turns every miss into an error (`CassetteMiss`), so a variant that should be free proves it is free. Such a
  run makes no model call, so the metric run policy counts it as a free stage: run it first, after a change to scoring or parsing,
  and pay for the real calls only if it passes.

## Honest results

A replayed response is the answer of the prompt as it was when recorded. Change the prompt, the model or any parameter and the key
changes, so the result is measured on a fresh answer. A change to the model's behaviour behind the same name is not visible to the
cassette: take a measurement you will `--record` for a decision with a fresh cassette folder (or none).

See [When metrics are run](../explanation/when-metrics-are-run.md) for why a free stage comes first.
