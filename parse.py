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
    def __init__(self, message, index=None, *args, context=None):
        super().__init__(message, *args)
        self.index = index
        self.context = context

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
                                        context=escape_sequence)
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
                                context=unfinished_escape_sequence)
    if end_delimiter:
        unfinished_token = string[token_start_index:]
        raise TokenizationError("Unfinished quoted token",
                                index=token_start_index,
                                context=unfinished_token)
    return token_end_index, "".join(token_chars) if found_token else None

def read_tokens(string):
    tokens = []
    index = 0
    while index < len(string):
        index, token = read_token(string, index)
        if token:
            tokens.append(token)
    return tokens
