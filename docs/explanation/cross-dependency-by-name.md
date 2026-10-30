# Depend on other solutions by name

When one solution's implementation needs another solution, the obvious route is an import: the report imports the memory
store. That ties the report to one store, so swapping the store means editing the report, and every alternative of one solution
has to know every alternative of the other. ESOI's answer is that implementations depend on **solutions**, never on other
implementations, and the dependency is resolved **by name** when the program is assembled.

## Why a name and not an import

- **The seat is the contract.** A solution is declared once as an interface (a Protocol class). An implementation says "I need
  a `store`" by typing a constructor parameter with that interface. It imports the contract, never an alternative.
- **A name is data.** Which store to use can live in configuration, a database row or an environment variable, and change
  without touching code. An import path cannot be data safely: a path from a file is a way to run code nobody reviewed.
  A name is checked against a narrow pattern and against the list of names the seat has, so a typo or a hostile value fails
  instead of importing something.
- **The records already say it.** `implementations.csv` has a `uses_solution_ids` column. With needs read from the typed
  parameters, the column is derived and checked rather than written by hand, and the graph of "who needs whom" can be tested:
  no cycles among default arms, every need met, a solution with no default arm marked as supplied by the consumer.
- **Failures come early.** Building in dependency order at startup means a cycle or an unmet need stops the program before it
  serves anything, with the chain named, instead of failing on the first call that happens to reach it.
- **Cost is paid once.** Resolution happens in `assemble`, then the result is frozen. A call does no lookup, takes no lock and
  cannot be re-pointed by a later registration.

## What this does not mean

It does not mean string-keyed lookup everywhere. Within one package, plain imports of plain code are fine. Names are for the
seams where more than one implementation is possible or wanted: that is exactly where a solution is declared.

Nor does it mean a plugin system with entry points or a scan of the disk. Arms are found only from three places: a `register`
call in the consumer's own code (trusted, it is the consumer's code), the arm's declaration in the package's own modules, and
the package's own records or packaged snapshot, where the module must start with the package name and lie inside the
package folder. The library never imports the application that uses it.

How to use it is in [Assemble the parts of a program by name](../guides/assemble-by-name.md). The part of this that is
general, and the part that is a particular application's, are separated in [What belongs where](what-belongs-where.md).
