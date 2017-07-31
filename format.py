import decimal

import model
import util

from util import DELIMITER_CHARS, DELIMITER_PREFERENCE, ESCAPE_CHARS

def escape(token, chars):
    return "".join(char if char not in chars else ESCAPE_CHARS[0] + char
                   for char in token)

def quote_with_delimiter(token, delimiter):
    end_delimiter = DELIMITER_CHARS[delimiter]
    escaped_token = escape(
        token, ESCAPE_CHARS + [delimiter, end_delimiter])
    return delimiter + escaped_token + end_delimiter

def quote(token):
    if (
            all(char not in token for char in DELIMITER_CHARS) and
            all(char not in token for char in ESCAPE_CHARS) and
            all(not char.isspace() for char in token)):
        return token
    # Note that min returns the first minimum element, if there are
    # multiple ones that have the same key.
    return min((quote_with_delimiter(token, delimiter)
                for delimiter in DELIMITER_PREFERENCE),
               key=len)

def format_date(date):
    return date.strftime("%x")

def format_time(date):
    return date.strftime("%X")

def format_transaction(transaction):
    tokens = []
    if isinstance(transaction, model.Credit):
        tokens.append("CREDIT")
    elif isinstance(transaction, model.Debit):
        tokens.append("DEBIT")
    elif isinstance(transaction, model.Transfer):
        tokens.append("TRANSFER")
    else:
        raise util.InternalError(f"Unexpected transaction class: "
                                 f"{transaction.__class__.__name__}")
    value = transaction.value.quantize(decimal.Decimal("1.00"))
    if isinstance(transaction, model.Debit):
        value = -value
    tokens.append(str(value))
    if isinstance(transaction, model.Credit):
        tokens.extend(["TO", quote(transaction.account.name)])
    elif isinstance(transaction, model.Debit):
        tokens.extend(["FROM", quote(transaction.account.name)])
    # We already established that it must be either a Credit, Debit,
    # or Transfer.
    else:
        tokens.extend(["FROM", quote(transaction.source_account.name),
                       "TO", quote(transaction.target_account.name)])
    if transaction.date:
        date_str = format_date(transaction.date)
        if transaction.with_time:
            date_str += " at " + format_time(transaction.date)
        tokens.extend(["ON", "DATE", quote(transaction.date)])
    if transaction.description:
        tokens.extend(["WITH", "DESCRIPTION", quote(transaction.description)])
    if transaction.category:
        tokens.extend(["IN", "CATEGORY", quote(transaction.category)])
    return " ".join(tokens)
