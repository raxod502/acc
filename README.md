**acc**: command-line accounting tool.

## Summary

`acc` is a Python package which provides both a Python API and a
command-line tool for reading and writing files which record financial
transactions in JSON format.

## Command-line usage

    usage: acc [-C <dir>] <subcommand> [<arg>...]

    Available subcommands:
        init [--git | --no-git] [--] <dir>
        import <importer> [<arg>...]
        help

Running `acc init` creates the specified directory, by default
initializes it as a Git repository, and creates a skeleton
`config.json` file in it. Since the structure of an `acc` library is
mostly up to you, that's all it does.

Running `acc import` allows you to import external data into an `acc`
ledger file. Importers are Python modules in the `acc.importers`
namespace, so for example you can use the `elevations_csv` importer by
running `acc import elevations_csv`. Each importer will expect
different command-line arguments.

## Ledger file format

Ledger files are pretty-printed JSON. The top level is a map with keys
`metadata` and `transactions` (other keys are untouched). `metadata`
is a map ... FIXME

    {
      "metadata": {
        "accounts": [
          <string>, ...
        ]
      },
      "transactions": [
        {
          "id": <string>,
          "description": <string>,
          "amount":
        }
      ]
    }

## File format

A *ledger file* is in JSON format. It contains a list of maps, each of
which may have a number of keys indicating metadata, as follows:

* `id` (string, required): Unique identifier used as a foreign key in
  other files. This is typically a randomly generated UUID.
* `amount` (floating-point, required): The monetary value of the
  transaction, in dollars. If this is negative then the direction of
  the transaction is reversed.
* `type` (string, required): Either `credit`, `debit`, or `transfer`.
  Identifies the type of the transaction.
* `account` (string, required unless `type` is `transfer`): The name
  of the account being credited or debited.
* `source-account` (string, required when `type` is `transfer`): The
  name of the account being debited.
* `target-account` (string, required when `type` is `transfer`): The
  name of the account being credited.
* `date` (string, optional): The date (and optionally time) of the
  transaction. This can be in any format parseable by
  `dateutil.parser`.
* `tags` (list of strings, optional): Arbitrary identifiers which can
  be used for categorization.

## Ledger import

Bank statements can be imported using *ledger importers*. An import
plugin is a Python module which produces `acc` transaction data,
presumably from an external source such as a bank website. Typically
bank statements are append-only ledgers, and updating them constitutes
appending to a file on disk.

## Ledger reconciliation

Links between different ledger files may be established using the `id`
field of transactions. The `links` key in a transaction contains a map
of account names to lists of transaction IDs.
