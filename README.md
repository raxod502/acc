## Deprecated

`acc` has been deprecated, since I no longer track my finances
manually.

## Summary

`acc` is a Python package which provides both a Python API and a
command-line tool for reading and writing files which record financial
transactions in JSON format.

## Command-line usage

    usage: acc [-C <dir>] [--git | --no-git] [--] <subcommand> [<arg>...]

    Available subcommands:
        init <dir>
        import <importer> [<arg>...]
        merge [--require-overlap | --no-require-overlap] [--] <source-ledger> <target-ledger>
        help

Running `acc init` creates the specified directory, by default
initializes it as a Git repository, and creates a skeleton
`config.json` file in it. Since the structure of an `acc` library is
mostly up to you, that's all it does.

Running `acc import` allows you to import external data into an `acc`
ledger file. Importers are Python modules in the `acc.importers`
namespace, so for example you can use the importer defined by the
`acc.importers.elevations_csv` module by running `acc import
elevations_csv`. Each importer will expect different command-line
arguments. Generally they will be given some file as input and produce
a ledger file containing the imported data.

Running `acc merge` allows you to integrate newly imported data into
an existing ledger without overwriting it. By default, there must be
some overlap between the ledgers (all fields except the IDs must
match), or the target ledger must be empty.

By default, if your `acc` library is version-controlled with Git,
`acc` will ensure that there are no uncommitted changes before an
action, and commit changes after the action is complete (if it
succeeded).

## Configuration

Configuration of `acc` is done by creating a file `config.json` in
some superdirectory of the working directory. If no `config.json` is
found then default configuration is used.

`config.json` is in JSON format. The top level must be a map. It
optionally has key `aliases`, which is a map of alias names (strings)
to alias definitions (strings).

When `acc` is invoked and the first argument matches a defined alias,
the definition of the alias is read from configuration and split
using [`shlex.split`][shlex] (so whitespace can be included in
arguments via quoting). Then the first argument is replaced with all
arguments taken from the alias definition, and command lookup resumes.
It is possible to create an alias to an existing command. It will be
expanded once before delegating to the existing command. Creating
mutually recursive aliases has undefined behavior.

Here is an example of an alias definition:

    "import-checking": "import elevations_csv --from external/checking.csv --to import/checking.json --account checking"

## Ledger file format

Ledger files are pretty-printed JSON. The top level is a map with keys
`metadata` and `transactions` (other keys are allowed and left
untouched). `metadata` is a map with key `accounts` (other keys are
allowed and left untouched). `accounts` is a list of strings (without
duplicates) naming the accounts that are tracked in this ledger file.
`transactions` is a list of maps, each identifying a distinct
transaction that has occurred. Transaction maps have keys `id`
(required), `description`, `amount` (required), `type` (required),
either `account` (when `type` is `debit` or `credit`) or
`source-account` and `target-account` (when `type` is `transfer`), and
`date` (required), `tags`, and `references` (other keys are allowed
and left untouched). `id` is a unique string for the transaction
(typically an auto-generated GUID). `description` is a human-readable
string recording the purpose of the transaction. `amount` is a
floating-point number naming the transaction size in dollars. `type`
may be either `debit`, `credit`, or `transfer` and describes how the
`amount` of the transaction affects the balances of its `account`
and/or `source-account` and `target-account` (`credit` means balance
of `account` is increased by `amount`; `debit` means balance of
`account` is decreased by `amount`; `transfer` means balance of
`source-account` is decreased by `amount` and balance of
`target-account` is increased by `amount`). `account`,
`source-account`, and `target-account` are strings naming accounts
that were listed under `accounts` in `metadata`. `date` is a string
identifying the date and/or time of the transaction, in format either
`%Y-%m-%d` or `%Y-%m-%d %H:%M:%S%z` (see [strftime format][strftime]).
`tags` is a list of strings identifying categories for filtering and
aggregation. `references` is a map with string keys; each value is a
map with keys `primary` and `foreign` (both optional). The values for
each of those keys are lists of transaction IDs, with `primary` IDs
referencing other transactions in the same ledger and `foreign` IDs
referencing other transactions in the ledger identified (in a manner
specified on the command line) by the key in the `references` map.

## TODO

* Implement ledger reconciliation

[shlex]: https://docs.python.org/3/library/shlex.html#shlex.split
[strftime]: http://strftime.org/
