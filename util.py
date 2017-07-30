def make_repr(self, keys):
    classname = self.__class__.__name__
    keyvals = []
    for key in keys:
        keyvals.append(f"{key}={repr(getattr(self, key))}")
    body = ", ".join(keyvals)
    return f"{classname}({body})"
