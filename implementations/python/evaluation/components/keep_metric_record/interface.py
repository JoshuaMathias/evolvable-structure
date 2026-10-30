"""The metric-record function. Every implementation is ONE object with this signature:

    record(kind: str, args: dict) -> dict

``kind`` names what is asked of the record, ``args`` the case, and the dict is what the implementation found. A throwaway
repository written by ``esoi.scaffold.init`` is the world (``metric_record_fixture``), so the records, the results log and the
evaluation component the metric is read from are the real shapes.

Kinds and what comes back:
  milestone   args {cell}                         -> {number, text, target}: the next open milestone of a milestones cell
  slice       args {request, folder, setup, chooser} -> {solution_id, metric_id, milestone_number}: ids are "" for no slice
  reading     args {meters, when, budget}         -> {value, meter, note, announced}: one bounded reading
  arm         args {meter, setup, spy}            -> {value, spawned, argv, leaked}: a meter over the repository's own metric
  result      args {source, before, after, reason} -> {error}: the exception name, "" for a result that was accepted
  reconcile   args {rows, limit}                  -> {sources, disagrees, values, line}: the rows as a payload shows them
  iteration   args {request, folder, meters, worker, did_work, source} -> {rows, block, reads}: the record of one piece of work

The cases are the ways a record goes wrong: a claim taken for a measurement, a stale row taken for the tree as it is, a metric
read by running an arm that could spend money, a reading that holds the work back, a number a model typed taken for a number.
No model is called.
"""
