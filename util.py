def get_vals(self, keys):
    return [getattr(self, key) for key in keys]

def make_repr(self, keys):
    classname = self.__class__.__name__
    keyvals = []
    for key in keys:
        keyvals.append(f"{key}={repr(getattr(self, key))}")
    body = ", ".join(keyvals)
    return f"{classname}({body})"

class Attributes:
    def __repr__(self):
        return make_repr(self, self._keys)

    def __eq__(self, other):
        return (type(self) == type(other) and
                get_vals(self, self._keys) == get_vals(other, other._keys))

    def __hash__(self):
        return hash(get_vals(self, self._keys))

class InternalError(Exception):
    pass

# Note: it is assumed that nothing in DELIMITER_CHARS or ESCAPE_CHARS
# is whitespace.

DELIMITER_CHARS = {
    "|": "|",
    "<": ">",
    '"': '"',
    "'": "'",
}

DELIMITER_PREFERENCE = ["|", "/", "<", '"', "'"]

ESCAPE_CHARS = ["\\"]
