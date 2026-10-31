# Override only what differs, and say why

A hub that has measured its solutions ships the best-known arm of each as a default. Someone who uses the hub should not have to
restate any of that: one line adopts every default. Someone who builds on the hub (a child) differs in a few places, and should write
down only those.

## Why hierarchical

Without a link between the two packages a child copies the hub's defaults, and the copies drift. When the hub improves a default,
every child that copied the old one keeps it without knowing. With a parent, the cascade ends in the parent's defaults, so a child that
states nothing for a solution gets whatever the hub currently ships, and a child that states something differs on purpose.

## Why every override says why

A default is the arm a metric picked for the cases that metric holds. A child that overrides it claims its situation is different or
its measurement says otherwise. That claim belongs in the child's own ESOI records: the problem it has that the default does not
solve, the ideal it is after, or the metric whose result differs. A choice that cites none is a preference that cannot be examined,
and it will outlive the reason it was made for. So a choice carries `reasons`, `explain` shows them next to the arm, and rule S35
reports an override that cites no record of the child's own. The text `unconfirmed:` is allowed as a placeholder (the work is not yet
done), but it never satisfies the rule, so it stays visible until a record replaces it. A waiver can name the pending decision, as with
the other rules that accept exceptions.

## What stays as it was

A package without a parent assembles as before, and a repository without a `[parent]` table is never checked by S35. The rule is not
in the way of a first adoption: it only asks for reasons where a parent exists to differ from. How to use it is in
[Build on another package's defaults and say why you differ](../guides/hierarchical-defaults.md).
