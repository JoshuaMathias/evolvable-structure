"""The consideration-verdict function, the paid stage of Solution Consideration. Every implementation is ONE function:

    verdict(kind: str, args: dict) -> {"text": the model's reply, "verdict": "adopt" | "reject" | "measure first" | ""}

Given a solution and a matter (``args.task``), a cheap model answers with a verdict and the records it rests on. The arms differ only
in what the model is given: the prompt the solution's network forms (with the knowledge the situation chooses) or the solution's own
record alone. Every case's deciding record is held only in the network: an arm that already lost on the solution's cases, recorded in
the results log (a synthetic repository shaped like the motivating incident, and this repository's own records). A case passes when
the verdict is the one the records support and the reply cites the deciding record.
An implementation module in ``impls/`` exposes ``build(meter) -> verdict``. Both arms call a model (PAID).
"""
