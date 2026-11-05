# Keep records beside the code

Use this when you want the specification of each solution in the folder that holds its code, so a person opening a code folder sees
what it is for and a person opening a specification is one folder from its code. The standard is
[records beside the code](../reference/records-beside-code.md).

Any language works: records point to code by `filepath`, and a repository without Python records its entry call in the solution's
`usage_notes`. If your build or framework fixes the folder structure, keep the `esoi/` folder instead; both are described in
[the standard](../reference/records-beside-code.md#both-layouts-any-language).

## Adopt it

1. List the folders that may hold records in `esoi.toml`:

   ```toml
   [records]
   beside_code = ["mypackage", "mypackage/*"]
   ```

2. See what would move, then move it:

   ```
   esoi records place            # a dry run: each record, from where to where
   esoi records place --apply    # move the records and write the README of every folder that now holds records
   ```

   A record goes to the folder of the code it describes (the lowest listed folder that holds all of a solution's code). Rows that
   belong to a sub-intent stay in its folder.

3. Run `esoi check --write-docs`. If your configuration measures code with `code_paths`, exclude the record files and READMEs
   inside the code folders so that editing a record does not make a recorded result stale (for example
   `":(exclude,glob)**/solutions.csv"`, one entry per record file name, and `":(exclude,glob)**/README.md"`). Give the components in
   `components.csv` the paths of the record files and READMEs the code folders now hold.

4. Commit the moved records with their READMEs.

## A sub-intent beside its code

Make a folder named by the sub-intent's id inside a code folder that `beside_code` lists, put its `intent.csv` there (its `implements`
names the parent implementation, which names the folder back in `sub_intent`), and give it the record files for what it holds. Add a
sub-intent only when it states opportunities that do not emerge from its parent
([when to create a sub-intent](../explanation/when-to-create-a-sub-intent.md)); otherwise a code folder is a solution folder.

## Keep it navigable

`esoi check --findings` lists what deviates from the standard, each with its next action (rule S40): a solution whose spec and code are
more than one link apart, a code folder with no README, a record kept twice. It never fails the check. To see how the layout
compares with the esoi folder on your repository, run the metric: `esoi run navigable_records --impl beside_code`, and the same with
`--impl esoi_folder`, with `ESOI_GLANCE_ADOPTERS` naming your repository.

## Go back

`esoi records gather --apply` moves every record of the top intent back into the structure folder; remove `beside_code` from
`esoi.toml` afterwards.

## Programs that read the records

A program reads the registry (`esoi.structure.intent_registry.registry.load(config)`) or the spec index, which merge every folder. A program that read
`esoi/solutions.csv` and the other record files directly must read the tree instead (`esoi.structure.intent_registry.intents.folders(config)` lists the folders,
`esoi.structure.intent_registry.intents.read_rows(config, "solutions.csv")` the rows).
