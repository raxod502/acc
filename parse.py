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

class TokenizationError(Exception):
    def __init__(self, message, index=None, *args, content=None):
        super().__init__(message, *args)
        self.index = index
        self.content = content

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

CLAUSE_NAMES = ["category", "date", "description", "from", "time", "to"]

CLAUSE_PREFIXES = {
    "category": ["and", "in", "using", "with"],
    "date": ["and", "at", "on", "using", "with"],
    "description": ["and", "using", "with"],
    "from": ["and"],
    "time": ["and", "at", "using", "with"],
    "to": ["and"],
}

CLAUSE_SUFFIXES = {
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

class Clause:
    def __init__(self, name, argument):
        self.name = name
        self.argument = argument

    def __repr__(self):
        return util.make_repr(self, ["name", "argument"])

class GroupingError(Exception):
    def __init__(self, message, *args, content=None):
        super().__init__(message, *args)
        self.content = content

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
