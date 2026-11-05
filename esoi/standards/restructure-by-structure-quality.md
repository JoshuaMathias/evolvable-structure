# Restructure by Structure Quality

**Read when:** Editing solution records, implementation records, intent records, an interface or a flow file: any merge, split, adoption, interface change or moved module.

**Problem it prevents:** A restructuring kept because it looked tidier, when the structure scored lower (a merge once left 31 arms off their interface and nobody measured it).

**Tags:** restructuring, low-quality-code
**Paths:** esoi/**/solutions.csv; esoi/**/implementations.csv; esoi/**/intent.csv; implementations/python/esoi/**/solutions.csv; implementations/python/esoi/**/implementations.csv; implementations/python/esoi/**/intent.csv; implementations/python/esoi/**/interface.py; implementations/python/esoi/**/flow.py
**Rule:** Before restructuring run `esoi structure-quality`, after it run `esoi structure-quality --compare <before> <after>`, keep the change only if the balanced number holds or rises, and state the reason in the commit.

A restructuring is an alternative structure, so it is compared before and after like any alternative
([the order of building](../../docs/explanation/the-order-of-building.md), steps 1, 2 and 6). Name the commit before the change as `<before>` and the
working tree (`.`) or the new commit as `<after>`. When the number falls, the commit says what the number does not see and why the structure is
better. How: [measure structure quality](../../docs/how-to/measure-structure-quality.md).
