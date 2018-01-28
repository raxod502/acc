import datetime

USAGE = """[-C <dir>] <subcommand> [<arg>...]

Available subcommands:
    init [--git | --no-git] [--] <dir>
    config <key> [<val>]
    import <importer> [--to <account>] [--] [<arg>...]
    merge <account> [--to <account>]
    help"""

SUBCOMMAND_USAGE = {
    "init": "[--git | --no-git] [--] <dir>",
}

class IOWrapper:
    def __init__(self, io, program_name):
        self.io = io
        self.program_name = program_name

    def print_usage(self, message=None, command=None, stream=None):
        if message is None:
            if command is None:
                message = USAGE
            else:
                message = command + " " + SUBCOMMAND_USAGE[command]
        if stream is None:
            stream = self.io.stderr
        usage = "usage: {} {}".format(self.program_name, message)
        print(usage, file=stream)

    def print(self, text):
        print(text, file=self.io.stdout)

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
    raise TypeError(
        "Object of type '{}' is not JSON serializable".format(type(obj)))

def subcommand_init(args, io):
    args_done = False
    using_git = True
    path = None
    for arg in args:
        if not args_done:
            if arg == "--git":
                using_git = True
                continue
            if arg == "--no-git":
                using_git = False
                continue
            if arg == "--":
                args_done = True
                continue
        if path is None:
            path = arg
            continue
        io.print_usage(command="init")
        return 1
    if path is None:
        io.print_usage(command="init")
        return 1
    if using_git and not io.which("git"):
        io.print_error("command not found: git")
        return 1
    parent = io.dirname(io.abspath(path))
    if not io.isdir(parent):
        io.print_error("no such directory: {}".format(parent))
        return 1
    if io.exists(path) or io.islink(path):
        io.print_error("path already exists: {}".format(path))
        return 1
    try:
        io.mkdir(path)
    except Exception as e:
        io.print_error(
            "could not create directory {}: {}".format(repr(path), str(e)))
        return 1
    result = io.run(["git", "init"], cwd=path)
    if result.returncode != 0:
        io.print_error("command failed: git init")
        return 1
    io.print("Set up acc in {}".format(io.join(io.abspath(path), "")))
    return 0

def subcommand_config(args, io):
    raise NotImplementedError

def subcommand_import(args, io):
    raise NotImplementedError

def subcommand_merge(args, io):
    raise NotImplementedError

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
        io.print_usage(stream=io.stdout)
        return 0
    io.print_usage()
