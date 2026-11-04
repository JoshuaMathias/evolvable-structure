# Component documents: whose document a file is

`components.csv` assigns every file to exactly one component by its `path` globs (rule S1). A solution that is a document, such
as a guide or the steps file, has no module for the coherence check to follow, and the folder glob that owns it (`docs/**`) says
nothing about which solution it is. The optional `documents` column names the specific files that are one solution's documents.

## The column

`documents` holds entries `path=solution-id` separated by `;`, on the component row whose `path` already owns the file:

```
component_id,layer,path,role,solutions,documents
documentation,docs,docs/**,Guides.,docs-and-templates;the-steps,docs/how-to/apply-by-hand.md=the-steps;docs/README.md=docs-and-templates
```

The column is optional; a file without it is read as having no documents named.

## Rule S1 for documents

Documents are a second ownership, exclusive by solution rather than by glob. The component still owns the file, so a file keeps
one component. Rule S1 also reports an entry that:

- has no `=solution-id`, or names a solution that is not in `solutions.csv`;
- names a path that is not a file of the repository, or one the row's own `path` does not match;
- names a document that another entry gives to a different solution (a document has one owner).

A solution may own many documents. A folder a component owns as a whole makes no document anyone's.

## Use in the coherence check

Evidence E5 of `python3 -m esoi.coherence` reads this ownership: a markdown link, image, reference definition or include
directive in a document only the user owns, pointing at a document only the used owns, is strong evidence for the recorded
`uses` edge. A solution's selected implementation that names a document as its `filepath` owns it too. Links inside fenced code,
inline code or HTML comments, URLs and bare mentions of a path never count. See
[Why prose is not evidence](../explanation/why-prose-is-not-code-evidence.md).
