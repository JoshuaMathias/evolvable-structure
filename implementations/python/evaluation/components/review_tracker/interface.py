"""The tracker function. Every implementation is ONE function with this signature:

    track(kind: str, args: dict) -> dict

The review tracker is the intent network as sheet tabs. Its structural columns must follow the registry (a stale tab
is called stale), its ``tracking_*`` columns are the reviewers' own and survive a rebuild, the leaderboard's verdict
reaches the solutions tab, and the parent-link columns of the records appear on the tabs.

Kinds and the dict an implementation returns, over the clean fixture repository with ``args["edits"]`` applied:
  tracker   args {edits, rebuild?: bool, tab?: str, key?: str, column?: str}
            -> {"stale": [tabs out of date before a rebuild], "value": the cell at (tab, key, column) after the rebuild,
                "header": the tab's columns, "rows": row count of the tab}
An implementation module in ``impls/`` exposes ``build(meter) -> track``. No implementation here calls a model.
"""
