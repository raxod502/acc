**acc**: lightweight, version-controlled, human-readable financial
records on the command line.

## Caveat

This software does not exist yet! I am practicing "README-driven
development". This text is a preliminary sketch of the functionality I
want to eventually create, and should not be considered a real
specification.

## Preview

`acc` manages an *accounts repository*. This consists of a primary
*transactions file*, a *configuration file*, as well as *import files*
and *associated resources*. Usually, the accounts repository is placed
under version control using Git.

The transactions file and import files are human-readable, generally
append-only ledgers which are structured in such a way as to be both
easy to modify by hand and unambiguous to parse by `acc`.

Ledgers are structured as a sequence of *transactions*. Each
transaction has a *date*, *description*, and *type*. Additionally,
each transaction is either a *credit*, *debit*, or *transfer*. The
former two types of transaction have an associated *account*.
Transfers have both a *source account* and *destination account*.
Finally, each transaction has a unique *id*, or identifier.

This information is structured in the *transaction language*, an
`acc`-specific DSL remniscent of SQL. Here is an example transaction:

    TRANSFER 3000.00 FROM checking TO saving ON DATE 7/15/17

The transaction language is quite flexible. For example, you could
also write that transaction as follows:

    t 3000

In this case, `acc` would check your configuration file to determine
the default source and destination accounts, and default to the
current date. You can request `acc` to reformat your transaction file
to make things prettier and less ambiguous, however. These
reformatting operations are of course quite safe since `acc` makes a
commit before and after each operation, by default.

## Components

The implementation of `acc` consists of many distinct, largely
independent components:

* The *data format* is a specification of the internal representation
  of transactions and ledgers. It provides methods for performing
  basic introspection, creation, and modification of these objects.
* The *transaction parser* is an algorithm that transforms a
  plain-text specification of a transaction into the internal data
  format. This easily covers ledger parsing as well, since a ledger is
  just a list of transactions, one per line. The transaction parser is
  capable of producing useful error messages and resolving syntactical
  ambiguities.
* The *transaction formatter* is an algorithm that can transform the
  internal representation of a transaction into a standard plain-text
  format.
* The *query parser* is an algorithm that transforms a plain-text
  search query into an internal representation.
* The *query engine* is an algorithm that uses the internal
  representation of a query to produce a list of matching
  transactions.
* The *command-line interface* dispatches commands to the various
  modules of `acc`.
* The *REPL* provides an alternative, interactive interface to `acc`
  functionality.
* The *transaction editor* provides an interactive interface for
  editing information about a transaction, or for creating a new one.
* The *ledger editor* provides an interface interface for re-ordering,
  deleting, or inserting transactions in a ledger.
* The *configuration processor* handles reading and writing data
  stored in the user's configuration file.
* The *version-control interface* provides an abstraction for safely
  writing data to disk while interfacing with Git to provide safety
  and versioning.
