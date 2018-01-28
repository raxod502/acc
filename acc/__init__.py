import datetime
import importlib

## Exceptions

class Exit(Exception):
    pass

class Success(Exit):
    pass

class Failure(Exit):
    pass

class UsageError(Failure):
    pass

class FilesystemError(Failure):
    pass

class ExternalCommandError(Failure):
    pass

## Usage

USAGE = """[-C <dir>] <subcommand> [<arg>...]

Available subcommands:
    init [--git | --no-git] [--] <dir>
    config <key> [<val>]
    import <importer> [<arg>...]
    merge <account> [--to <account>]
    help"""

SUBCOMMAND_USAGE = {
    "init": "[--git | --no-git] [--] <dir>",
    "import": "<importer> [<arg>...]",
}

def usage():
    return UsageError(USAGE)

def subcommand_usage(subcommand):
    return SUBCOMMAND_USAGE[subcommand]

## IOWrapper

class IOWrapper:
    def __init__(self, io, program_name):
        self.io = io
        self.program_name = program_name

    def print(self, text, stream=None):
        if stream is None:
            stream = self.io.stdout
        print(text, file=self.io.stdout)

    def print_error(self, text):
        message = "{}: {}".format(self.program_name, text)
        self.print(message, stream=self.io.stderr)

    def print_usage(self, usage, stream=None):
        if stream is None:
            stream = self.io.stderr
        message = "usage: {} {}".format(self.program_name, usage)
        self.print(message, stream=stream)

    def __getattr__(self, name):
        return getattr(self.io, name)

## Miscellaneous

def json_serializer(obj):
    if isinstance(obj, datetime.date):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, datetime.datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S%z")
    raise TypeError(
        "Object of type '{}' is not JSON serializable".format(type(obj)))

## Subcommands
### init

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
        raise subcommand_usage("init")
    if path is None:
        raise subcommand_usage("init")
    if using_git and not io.which("git"):
        raise ExternalCommandError("command not found: git")
    parent = io.dirname(io.abspath(path))
    if not io.isdir(parent):
        raise FilesystemError("no such directory: {}".format(parent))
    if io.exists(path) or io.islink(path):
        raise FilesystemError("path already exists: {}".format(path))
    try:
        io.mkdir(path)
    except Exception as e:
        raise FilesystemError(
            "could not create directory {}: {}".format(repr(path), str(e)))
    result = io.run(["git", "init"], cwd=path)
    if result.returncode != 0:
        raise ExternalCommandError("command failed: git init")
    io.print("Set up acc in {}".format(io.join(io.abspath(path), "")))

### config

def subcommand_config(args, io):
    raise NotImplementedError

### import

def subcommand_import(args, io):
    if not args:
        raise subcommand_usage("import")
    importer_name, *args = args
    module_name = "acc.importers.{}".format(importer_name)
    if not importlib.util.find_spec(module_name):
        raise FilesystemError("no such module: {}".format(module_name))
    importer = importlib.import_module(module_name)
    try:
        importer.run(args, io)
    except UsageError as e:
        raise UsageError("import " + importer_name + " " + str(e))

### merge

def subcommand_merge(args, io):
    raise NotImplementedError

## Command line

SUBCOMMANDS = {
    "init": subcommand_init,
    "config": subcommand_config,
    "import": subcommand_import,
    "merge": subcommand_merge,
}

def command_line(program_name, args, io):
    io = IOWrapper(io, program_name)
    try:
        while args and args[0] == "-C":
            if len(args) == 1:
                raise usage()
            path = args[1]
            if not io.isdir(path):
                raise FilesystemError("no such directory: {}".format(path))
            io.chdir(path)
            args = args[2:]
        if not args:
            raise usage()
        subcommand, *args = args
        if subcommand in SUBCOMMANDS:
            try:
                SUBCOMMANDS[subcommand](args, io)
            except UsageError as e:
                raise UsageError(subcommand + " " + str(e))
        elif subcommand in ("help", "-h", "-help", "--help", "-?"):
            io.print_usage(stream=io.stdout)
        else:
            raise usage()
    except UsageError as e:
        io.print_usage(str(e))
        return 1
    except Failure as e:
        io.print_error(str(e))
        return 1
    except Success:
        pass
    return 0
