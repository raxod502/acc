import acc

import csv
import dateutil.parser

## Parsing

InvalidInputError = acc.UserDataError

ACCOUNTS = (
    "cash",
    "elevations-checking",
    "elevations-savings",
    "roth-ira",
    "vanguard-brokerage",
    "inherited-ira",
    "claremont-cash",
    "us-treasury-bonds",
)

HEADER_ROWS = 3
FOOTER_ROWS = 1

def parse_money(money, row_num):
    if not money:
        return 0.0
    if money.startswith("$"):
        money = money[1:]
    elif money.startswith("-$"):
        money = "-" + money[2:]
    else:
        raise InvalidInputError("malformed monetary value in row {}: {}"
                                .format(row_num, repr(money)))
    try:
        return float(money.replace(",", ""))
    except ValueError:
        raise InvalidInputError("malformed monetary value in row {}: {}"
                                .format(row_num, repr(money)))

def parse_row(row, row_num):
    date = row[0]
    description = row[2]
    transaction_id = row[3]
    category = row[4]
    pending = row[5]
    deltas = row[7:7+len(ACCOUNTS)]

    try:
        date = dateutil.parser.parse(date)
    except ValueError as e:
        raise InvalidInputError("malformed date in row {}: {}".format(row_num, repr(date)))
    if not description:
        raise InvalidInputError("missing description in row {}".format(row_num))
    if not transaction_id:
        raise InvalidInputError("missing transaction ID in row {}".format(row_num))
    if not category:
        raise InvalidInputError("missing category in row {}".format(row_num))
    if pending not in ["", "yes"]:
        raise InvalidInputError("malformed 'pending' specifier in row {}: {}"
                                .format(row_num, repr(pending)))
    pending = bool(pending)

    deltas = list(map(lambda money: parse_money(money, row_num), deltas))
    nonzero_indices = []
    for idx, delta in enumerate(deltas):
        if delta != 0.0:
            nonzero_indices.append(idx)
    if len(nonzero_indices) not in (1, 2):
        deltas = [deltas[idx] for idx in nonzero_indices]
        raise InvalidInputError(
            "need exactly one or two deltas in row {}, got {}: {}"
            .format(row_num, len(deltas), repr(deltas)))
    if len(nonzero_indices) == 2:
        transaction_type = "transfer"
        delta1 = deltas[nonzero_indices[0]]
        delta2 = deltas[nonzero_indices[1]]
        if delta1 != -delta2:
            raise InvalidInputError(
                "unbalanced transfer in row {}, got deltas {} and {}"
                .format(delta1, delta2))
        amount = abs(delta1)
        if delta1 < 0:
            source = ACCOUNTS[nonzero_indices[0]]
            target = ACCOUNTS[nonzero_indices[1]]
        else:
            source = ACCOUNTS[nonzero_indices[1]]
            target = ACCOUNTS[nonzero_indices[0]]
    else:
        amount = deltas[nonzero_indices[0]]
        if amount > 0:
            transaction_type = "credit"
        else:
            transaction_type = "debit"
            amount = -amount
        account = ACCOUNTS[nonzero_indices[0]]

    trans = {
        "id": acc.random_transaction_id(),
        "description": description,
        "amount": amount,
        "type": transaction_type,
        "date": date,
        "tags": [category],
        "pending": pending,
    }

    if transaction_type == "transfer":
        trans["source-account"] = source
        trans["target-account"] = target
    else:
        trans["account"] = account

    return trans

def read_csv(csv_file):
    transactions = []
    with open(csv_file, newline="") as f:
        lines = list(csv.reader(f))
    lines = lines[HEADER_ROWS:-FOOTER_ROWS]
    for idx, row in enumerate(lines, HEADER_ROWS + 1):
        transactions.append(parse_row(row, idx))
    return {
        "metadata": {
            "accounts": ACCOUNTS,
        },
        "transactions": transactions,
    }

## Command line

USAGE = "--from <csv-file> --to <json-file>"

def usage():
    return acc.UsageError(USAGE)

def run(args, io):
    csv_path = None
    json_path = None
    while args:
        if args[0] == "--from":
            if len(args) == 1:
                raise usage()
            csv_path = args[1]
            args = args[2:]
        elif args[0] == "--to":
            if len(args) == 1:
                raise usage()
            json_path = args[1]
            args = args[2:]
        else:
            raise usage()
    if csv_path is None or json_path is None:
        raise usage()
    try:
        ledger = read_csv(csv_path)
    except OSError as e:
        raise acc.FilesystemError(
            "could not read file {}: {}".format(repr(csv_path), str(e)))
    ledger_str = acc.serialize_ledger(ledger)
    json_dir = io.dirname(json_path)
    try:
        io.makedirs(json_dir, exist_ok=True)
    except OSError as e:
        raise acc.FilesystemError(
            "could not create directory {}: {}".format(repr(json_dir), str(e)))
    try:
        with open(json_path, "w") as f:
            f.write(ledger_str)
            f.write("\n")
    except IOError as e:
        raise acc.FilesystemError(
            "could not write file {}: {}".format(repr(json_path), str(e)))
