import acc

import csv
import dateutil.parser
import uuid

## Parsing

HEADER_ROWS = 4

class InvalidInputError(Exception):
    pass

def random_id():
    return str(uuid.uuid4())

def parse_row(row, row_id):
    elevations_id = row[0]
    date = row[1]
    elevations_description = row[2]
    elevations_memo = row[3]
    debit_delta = row[4]
    credit_delta = row[5]
    elevations_balance = row[6]
    elevations_check_number = row[7]

    if not elevations_id:
        raise InvalidInputError("No transaction ID for row {}"
                                .format(row_id))

    try:
        date = dateutil.parser.parse(date)
    except ValueError:
        raise InvalidInputError("Could not parse date for row {}: {}"
                                .format(row_id, repr(date)))

    if not elevations_description:
        raise InvalidInputError("No description for row {}".format(row_id))

    if not elevations_memo:
        elevations_memo = None

    if debit_delta:
        try:
            debit_delta = float(debit_delta)
        except ValueError:
            raise InvalidInputError("Malformed debit for row {}: {}"
                                    .format(row_id, repr(debit_delta)))
    else:
        debit_delta = 0

    if credit_delta:
        try:
            credit_delta = float(credit_delta)
        except ValueError:
            raise InvalidInputError("Malformed credit for row {}: {}"
                                    .format(row_id, repr(credit_delta)))
    else:
        credit_delta = 0

    try:
        elevations_balance = float(elevations_balance)
    except ValueError:
        raise InvalidInputError("Malformed balance for row {}: {}"
                                .format(row_id, repr(elevations_balance)))

    if not elevations_check_number:
        elevations_check_number = None

    description = elevations_description
    if elevations_memo:
        description += ": " + elevations_memo

    if debit_delta and credit_delta:
        raise InvalidInputError("Both credit and debit for row {}"
                                .format(row_id))

    if not debit_delta and not credit_delta:
        raise InvalidInputError("Neither credit nor debit for row {}"
                                .format(row_id))

    if debit_delta:
        transaction_type = "debit"
        amount = -debit_delta
    else:
        transaction_type = "credit"
        amount = credit_delta

    return {
        "id": random_id(),
        "description": description,
        "amount": amount,
        "type": transaction_type,
        "date": date,
        "elevations_id": elevations_id,
        "elevations_description": elevations_description,
        "elevations_memo": elevations_memo,
        "elevations_balance": elevations_balance,
        "elevations_check_number": elevations_check_number,
    }

def read_csv(csv_file):
    transactions = []
    with open(csv_file) as f:
        reader = csv.reader(f)
        for i in range(HEADER_ROWS):
            next(reader)
        for idx, row in enumerate(reader, HEADER_ROWS + 1):
            transactions.append(parse_row(row, idx))
    return transactions

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
        transactions = read_csv(csv_path)
    except OSError as e:
        raise acc.FilesystemError(
            "could not read file {}: {}".format(repr(csv_path), str(e)))
    transactions_str = acc.serialize_transactions(transactions)
    json_dir = io.dirname(json_path)
    try:
        io.makedirs(json_dir, exist_ok=True)
    except OSError as e:
        raise acc.FilesystemError(
            "could not create directory {}: {}".format(repr(json_dir), str(e)))
    try:
        with open(json_path, "w") as f:
            f.write(transactions_str)
            f.write("\n")
    except IOError as e:
        raise acc.FilesystemError(
            "could not write file {}: {}".format(repr(json_path), str(e)))
