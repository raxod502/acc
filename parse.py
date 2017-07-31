import decimal

from decimal import Decimal

import model
import util

# Note: it is assumed that nothing in DELIMITER_CHARS or ESCAPE_CHARS
# is whitespace.

DELIMITER_CHARS = {
    '"': '"',
    "'": "'",
    "|": "|",
    "<": ">",
}

ESCAPE_CHARS = ["\\"]

class ParseError(Exception):
    def __init__(self, message, *args, content=None, row=None, column=None):
        super().__init__(message, *args)
        self.content = content
        self.row = row
        self.column = column

class TokenizationError(ParseError):
    def __init__(self, message, *args, index=None, content=None):
        super().__init__(message, *args, column=index, content=content)

def read_token(string, parsing_start_index):
    found_token = False
    token_chars = []
    end_delimiter = None
    escape_next_char = False
    token_start_index = None
    token_end_index = len(string)
    for index in range(parsing_start_index, len(string)):
        char = string[index]
        if not found_token:
            if not char.isspace():
                found_token = True
                token_start_index = index
                if char in DELIMITER_CHARS:
                    end_delimiter = DELIMITER_CHARS[char]
                elif char in ESCAPE_CHARS:
                    escape_next_char = True
                else:
                    token_chars.append(char)
        elif escape_next_char:
            if (char not in ESCAPE_CHARS and char != end_delimiter and not
                (not end_delimiter and
                 (char.isspace() or char in DELIMITER_CHARS))):
                last_char = string[index - 1]
                escape_sequence = f"{last_char}{char}"
                escape_sequence_index = index - 1
                raise TokenizationError("Malformed escape sequence",
                                        index=escape_sequence_index,
                                        content=escape_sequence)
            token_chars.append(char)
            escape_next_char = False
        elif char == end_delimiter:
            end_delimiter = None
            token_end_index = index + 1
            break
        elif not end_delimiter and (char.isspace() or char in DELIMITER_CHARS):
            token_end_index = index
            break
        elif char in ESCAPE_CHARS:
            escape_next_char = True
        else:
            token_chars.append(char)
    if escape_next_char:
        unfinished_escape_sequence = string[index - 1]
        escape_sequence_index = index - 1
        raise TokenizationError("Unfinished escape sequence",
                                index=escape_sequence_index,
                                content=unfinished_escape_sequence)
    if end_delimiter:
        unfinished_token = string[token_start_index:]
        raise TokenizationError("Unfinished quoted token",
                                index=token_start_index,
                                content=unfinished_token)
    return token_end_index, "".join(token_chars) if found_token else None

def read_tokens(string):
    tokens = []
    index = 0
    while index < len(string):
        index, token = read_token(string, index)
        if token:
            tokens.append(token)
    return tokens

CLAUSE_NAMES = [
    "account", "category", "date", "description", "from", "id", "time", "to"
]

CLAUSE_PREFIXES = {
    "account": ["and", "in", "using", "with"],
    "category": ["and", "in", "using", "with"],
    "date": ["and", "at", "on", "using", "with"],
    "description": ["and", "using", "with"],
    "from": ["and"],
    "id": ["and", "using", "with"],
    "time": ["and", "at", "using", "with"],
    "to": ["and"],
}

CLAUSE_SUFFIXES = {
    "account": [],
    "category": ["of"],
    "date": ["of"],
    "description": ["of"],
    "from": ["account"],
    "time": ["of"],
    "to": ["account"],
}

def matches(candidate, pattern):
    return pattern.casefold().startswith(candidate.casefold())

def matches_exactly(candidate, pattern):
    return pattern.casefold() == candidate.casefold()

class Clause(util.Attributes):
    def __init__(self, name, argument):
        self.name = name
        self.argument = argument
        self._keys = ["name", "argument"]

class InterpretationError(ParseError):
    def __init__(self, message, *args, content=None):
        super().__init__(message, *args, content=content)

def interpret_type_token(token):
    for type_ in ["credit", "debit", "transfer"]:
        if matches(token, type_):
            return type_
    raise InterpretationError("Malformed transaction type",
                              content=token)

def interpret_value_token(token):
    trimmed_token = token[1:] if token.startswith("$") else token
    try:
        value = Decimal(trimmed_token)
    except decimal.InvalidOperation:
        raise InterpretationError("Malformed transaction value",
                                  context=token)
    return value

def interpret_argument(argument, clause_name, config):
    interpretations = []
    for clause_argument in ["foo", "bar", "baz", "quux"]:
        if matches(argument, clause_argument):
            interpretation = Clause(clause_name, clause_argument)
            interpretations.append(interpretation)
    return interpretations

def interpret_token_group(tokens, config):
    interpretations = []
    for index, token in enumerate(tokens[:-1]):
        for clause_name in CLAUSE_NAMES:
            valid = True
            if matches(token, clause_name):
                for prefix in tokens[:index]:
                    if not any(
                            matches_exactly(prefix, clause_prefix)
                            for clause_prefix in CLAUSE_PREFIXES[clause_name]):
                        valid = False
                        break
                if not valid:
                    break
                for suffix in tokens[index + 1:-1]:
                    if not any(
                            matches_exactly(suffix, clause_suffix)
                            for clause_suffix in CLAUSE_SUFFIXES[clause_name]):
                        valid = False
                        break
                if not valid:
                    break
                argument = tokens[-1]
                interpretations.extend(interpret_argument(
                    argument, clause_name, config))
    return interpretations

def interpret_token_groups(tokens, config):
    if not tokens:
        return [[]]
    interpretations = []
    for length in range(2, len(tokens) + 1):
        head_interpretations = interpret_token_group(tokens[:length], config)
        if head_interpretations:
            tail_interpretations = interpret_token_groups(
                tokens[length:], config)
            for head in head_interpretations:
                for tail in tail_interpretations:
                    interpretations.append([head] + tail)
    return interpretations

def interpret_tokens(tokens, config):
    if len(tokens) < 2:
        raise InterpretationError("Transaction must provide type and value")
    type_token, value_token, *token_groups = tokens
    type_ = interpret_type_token(type_token)
    value = interpret_value_token(value_token)
    group_interpretations = interpret_token_groups(token_groups, config)
    if not group_interpretations:
        raise InterpretationError("No valid interpretations")
    return [(type_, value, interpretation)
            for interpretation in group_interpretations]

class NormalizationError(ParseError):
    def __init__(self, message, *args, content=None):
        super().__init__(message, *args, content=content)

def normalize_interpretation(type_, value, clauses, config):
    clause_map = {}
    for clause in clauses:
        if clause.name in clause_map:
            raise NormalizationError("Duplicate clause",
                                     content=clause.name)
        clause_map[clause.name] = clause.argument
    if "account" in clause_map and ("from" in clause_map or
                                    "to" in clause_map):
        raise NormalizationError("'account' is incompatible with "
                                 "'from' and 'to'")
    if "account" in clause_map and type_ == "transfer":
        raise NormalizationError("'account' cannot be used with transfers")
    if "from" in clause_map and type_ == "credit":
        raise NormalizationError("'from' cannot be used with credits")
    if "to" in clause_map and type_ == "debit":
        raise NormalizationError("'to' cannot be used with debits")
    options = {}
    if type_ == "credit":
        account = (clause_map.get("account") or
                   clause_map.get("to") or
                   config.default_credit_to_account())
        if not account:
            raise NormalizationError("Credit does not specify account "
                                     "and no default configured")
        options["account"] = model.Account(account)
        class_ = model.Credit
    elif type_ == "debit":
        account = (clause_map.get("account") or
                   clause_map.get("from") or
                   config.default_debit_from_account())
        if not account:
            raise NormalizationError("Debit does not specify account "
                                     "and no default configured")
        options["account"] = model.Account(account)
        class_ = model.Debit
    elif type_ == "transfer":
        to = clause_map.get("to") or config.default_transfer_to_account()
        from_ = (clause_map.get("from") or
                 config.default_transfer_from_account())
        if not to:
            raise NormalizationError("Transfer does not specify source "
                                     "account, and no default configured")
        if not from_:
            raise NormalizationError("Transfer does not specify target "
                                     "account, and no default configured")
        if to == from_:
            if "to" in clause_map and "from" in clause_map:
                raise NormalizationError("Transfer specifies identical source "
                                         "and target accounts")
            if "to" in clause_map:
                from_ = config.alternate_transfer_from_account()
                if not from_:
                    raise NormalizationError("Transfer has identical source "
                                             "and target accounts, and no "
                                             "alternate source configured")
            else:
                to = config.alternate_transfer_to_account()
                if not to:
                    raise NormalizationError("Transfer has identical source "
                                             "and target accounts, and no "
                                             "alternate target configured")
        options["source_account"] = model.Account(from_)
        options["target_account"] = model.Account(to)
        class_ = model.Transfer
    else:
        raise util.InternalError("Unexpected transaction type")
    options["value"] = value
    options["date"] = config.make_date(clause_map.get("date"),
                                       clause_map.get("time"))
    options["id_"] = clause_map.get("id") or config.make_id()
    return class_(**options)

def parse_transaction(string, config):
    tokens = read_tokens(string)
    interpretations = interpret_tokens(tokens, config)
    if len(interpretations) > 1:
        raise InterpretationError("More than one valid interpretation")
    interpretation = interpretations[0]
    transaction = normalize_interpretation(*interpretation, config)
    return transaction
