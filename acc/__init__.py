import datetime

USAGE_FORMAT = """usage: {} [-C <dir>] <subcommand> [<arg>...]

Available subcommands:
    init [<dir>] [--git | --no-git]
    config <key> [<val>]
    import <importer> [--to <account>] [--] [<arg>...]
    merge <account> [--to <account>]
    help"""

class IOWrapper:
    def __init__(self, io, program_name):
        self.io = io
        self.program_name = program_name

    def print_usage(self, stream=None):
        if stream is None:
            stream = self.io.stderr
        usage = USAGE_FORMAT.format(self.program_name)
        print(usage, file=stream)

    def print_error(self, text):
        message = "{}: {}".format(self.program_name, text)
        print(message, file=self.io.stderr)

    def __getattr__(self, name):
        return getattr(self.io, name)

def json_serializer(obj):
    if isinstance(obj, datetime.date):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, datetime.datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S%z")
    raise TypeError("Object of type '{}' is not JSON serializable".format(type(obj)))

def subcommand_init(args, io):
    pass

def subcommand_config(args, io):
    pass

def subcommand_import(args, io):
    pass

def subcommand_merge(args, io):
    pass

def command_line(program_name, args, io):
    io = IOWrapper(io, program_name)
    while args and args[0] == "-C":
        if len(args) == 1:
            io.print_usage()
            return 1
        path = args[1]
        if not io.isdir(path):
            io.print_error("no such directory: {}".format(path))
            return 1
        io.chdir(path)
        args = args[2:]
    if not args:
        io.print_usage()
        return 1
    subcommand, *args = args
    if subcommand == "init":
        return subcommand_init(args, io)
    if subcommand == "config":
        return subcommand_config(args, io)
    if subcommand == "import":
        return subcommand_import(args, io)
    if subcommand == "merge":
        return subcommand_merge(args, io)
    if subcommand in ("help", "-h", "-help", "--help", "-?"):
        io.print_usage(io.stdout)
        return 0
    io.print_usage()
