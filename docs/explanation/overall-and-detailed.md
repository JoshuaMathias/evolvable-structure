# The overall network and the detailed records

A repository has two levels of intent.

**The overall solution network** is written first, from the intent of the person who owns it (AI can draft it for
their review), and refined as the intent changes. It says why the repository exists, what it should
become, what it is defined to do, the alternatives to it, and how to tell whether it succeeds: problems, ideals, the
overall solution (with its areas), alternatives, and top metrics. It is short, in prose a newcomer can read in one
sitting, and it changes slowly. The template is [overall-solution-network.md](../templates/overall-solution-network.md).

**The detailed records** are the practical structures that implement it: a separate solution wherever a part has its
own definition of "best" that could affect the success of the intent, and no more, each with its implementations, its
metric, its cases and its results. They change as often as the code does.

## How they link

A detailed record names the part of the overall network it serves, in optional columns:

| Column | Names |
|---|---|
| `parent_problem_ids` | the overall problems this record is an aspect of |
| `parent_ideal_ids` | the overall ideals it pursues |
| `overall_solution_ids` | the area of the overall solution it belongs to |
| `parent_metric_ids` | the top metric it feeds |

A detailed solution may leave out its own problem and ideal when its parents are the problem and ideal it serves; add
its own when it solves a narrower difficulty. A check can verify that every parent id exists in the overall network, and
that every detailed solution names at least one parent.

## Why two levels

The overall network is where direction is set and reviewed. The detailed records are where the work is. Keeping them
separate lets the direction change without rewriting every record, and lets any detail be traced up to the reason it
exists. Each repository writes its own overall network: ESOI supplies the guidance and the tools, not the intent.
