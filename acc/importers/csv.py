#!/usr/bin/env python3

import csv
import dateutil.parser
import uuid

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

class InvalidInputError(Exception):
    pass

def random_id():
    return str(uuid.uuid4())

def parse_money(money):
    if not money.startswith("$"):
        raise InvalidInputError
    return float(money[1:])

def csv_row_to_transaction(row):
    date = row[0]
    description = row[2]
    transaction_id = row[3]
    category = row[4]
    pending = row[5]
    deltas = row[7:7+len(ACCOUNTS)]

    try:
        date = dateutil.parser.parse(date)
    except ValueError as e:
        raise InvalidInputError("Couldn't parse date: " + date)
    if not description:
        raise InvalidInputError
    if not transaction_id:
        raise InvalidInputError
    if not category:
        raise InvalidInputError
    if pending not in ["", "yes"]:
        raise InvalidInputError
    pending = bool(pending)

    deltas = list(map(parse_money, deltas))
    nonzero_indices = []
    for idx, delta in enumerate(deltas):
        nonzero_indices.append(idx)
    if len(nonzero_indices) not in (1, 2):
        raise InvalidInputError
    if len(nonzero_indices) == 2:
        transaction_type = "transfer"
        delta1 = deltas[nonzero_indices[0]]
        delta2 = deltas[nonzero_indices[1]]
        if delta1 != -delta2:
            raise InvalidInputError
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
        account = nonzero_indices[0]

    trans = {
        "id": random_id(),
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

def csv_file_to_transactions(filename):
    transactions = []
    with open(filename, newline="") as f:
        reader = csv.reader(f)
        # Skip the header.
        next(reader)
        for row in reader:
            transactions.append(csv_row_to_transaction(row))
    return transactions
