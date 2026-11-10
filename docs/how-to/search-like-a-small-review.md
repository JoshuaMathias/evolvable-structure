# Search like a small review

The method behind each step is in the [knowledge search standard](../reference/knowledge-search-standard.md); no model is called and nothing costs money.

1. **Look first.** Read the earlier investigations on the solution you are working on and on its ancestor solutions (`investigations.on_solution`
   with ancestors). A current review of the same question (not past its `refresh_on`) is the answer; a stale or partial one is extended. Link
   your own investigation to at least one solution (`solution:<id>` in `links`), going up to the solution its intent implements when nothing narrower fits.
2. **Choose the size** from the decision's weight: quick (reversible within a day, one implementation), standard (a selected arm, a metric, a
   registry area), full (hard to reverse, a shared dependency, licence, privacy, a public claim). When two fit, take the larger.
3. **Write the method before the first query.** The question in four slots (need, candidates including the strongest existing one,
   comparator, outcome), the decision, the criteria for inclusion and exclusion, the sources and the size. Date it.
4. **Search and log every query** with its source, the date and the number of hits.
5. **Screen.** Count what you found, what you left out and why (one count per reason), what you kept.
6. **Extract and grade each kept item:** claim, source, date, independent or not, how you verified it (opened, cross-checked,
   snippet, not opened), licence for code, grade A to D by the [public evidence grade](use-public-evidence.md#the-grade-in-short).
7. **Synthesize** (standard and full): known, contested, unknown. **State the limitations.**
8. **Decide per candidate:** adopt, adapt, build-on, reject, defer or no-candidate, with a reason.
9. **Apply it.** For each kept item name what it changed (`kind:record id`) or write `not-applied: reason`; add `investigation_id` to any knowledge row it produced.
10. **Set the refresh date** and run `esoi check`: the advice lists what the record lacks, what is past its refresh and what was never applied.

The records are two files beside `knowledge.csv`, `investigations.csv` and `investigation_items.csv`; their columns are in the standard.
