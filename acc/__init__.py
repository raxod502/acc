import acc.importers

import datetime
import importlib
import json
import pkgutil
import shlex
import uuid

## Exceptions

class Exit(Exception):
    pass

class Success(Exit):
    pass

class Failure(Exit):
    pass

class RawUsageError(Failure):
    pass

class UsageError(Failure):
    pass

class FilesystemError(Failure):
    pass

class ExternalCommandError(Failure):
    pass

class InternalError(Failure):
    pass

class UserDataError(Failure):
    pass

## Usage

USAGE = """[-C <dir>] <subcommand> [<arg>...]

Available subcommands:
    init [--git | --no-git] [--] <dir>
    import <importer> [<arg>...]
    help"""

SUBCOMMAND_USAGE = {
    "init": "[--git | --no-git] [--] <dir>",
    "import": "<importer> [<arg>...]",
}

def usage():
    return UsageError(USAGE)

def subcommand_usage(subcommand):
    return UsageError(SUBCOMMAND_USAGE[subcommand])

## IOWrapper

class IOWrapper:
    def __init__(self, io, program_name):
        self.io = io
        self.program_name = program_name

    def print(self, *args, stream=None, **kwargs):
        if stream is None:
            stream = self.io.stdout
        print(*args, file=self.io.stdout, **kwargs)

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

def quote_command(args):
    return " ".join(shlex.quote(arg) for arg in args)

def random_transaction_id():
    return str(uuid.uuid4())

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"

def is_datetime(date):
    return ":" in date

def serialize_ledger(ledger):
    transactions = []
    for transaction in ledger["transactions"]:
        transaction = dict(transaction)
        if "date" in transaction:
            date = transaction["date"]
            if date is None:
                date_str = None
            elif isinstance(date, datetime.date):
                date_str = date.strftime(DATE_FORMAT)
            elif isinstance(date, datetime.datetime):
                date_str = date.strftime(DATETIME_FORMAT)
            else:
                raise InternalError(
                    "cannot serialize date of type {}: {}"
                    .format(repr(type(date)), repr(date)))
            transaction["date"] = date_str
        transactions.append(transaction)
    ledger = dict(ledger)
    ledger["transactions"] = transactions
    return json.dumps(ledger, indent=2)

def deserialize_ledger(ledger_json):
    try:
        ledger = json.loads(ledger_json)
    except json.decoder.JSONDecodeError as e:
        raise UserDataError("malformed JSON: {}".format(str(e)))
    for transaction in ledger["transactions"]:
        if "date" in transaction:
            date = transaction["date"]
            try:
                if is_datetime(date):
                    date = datetime.datetime.strptime(DATETIME_FORMAT)
                else:
                    date = datetime.datetime.strptime(DATE_FORMAT).date()
            except ValueError:
                raise UserDataError("malformed date: {}".format(date))
            transaction["date"] = date
    return ledger

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
    config_file = io.join(path, "config.json")
    config = {
        "aliases": [],
    }
    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
    except OSError as e:
        raise FilesystemError(
            "could not write file {}: {}".format(repr(config_file), str(e)))
    io.print("Set up acc in {}".format(io.join(io.abspath(path), "")))

### import

def format_importer_list():
    importers = []
    for package in pkgutil.walk_packages(path=acc.importers.__path__):
        importers.append(package.name)
    return ("\n\nAvailable importers (modules in 'acc.importers' namespace):\n" +
            "\n".join("  - " + importer for importer in importers))

def subcommand_import(args, io):
    if not args:
        raise UsageError(SUBCOMMAND_USAGE["import"] + format_importer_list())
    importer_name, *args = args
    module_name = "acc.importers.{}".format(importer_name)
    if not importlib.util.find_spec(module_name):
        raise FilesystemError("no such module: {}".format(module_name) +
                              format_importer_list())
    importer = importlib.import_module(module_name)
    try:
        importer.run(args, io)
    except UsageError as e:
        raise UsageError(importer_name + " " + str(e))

## Configuration

def locate_dominating_file(filename, io, directory=None):
    if directory is None:
        directory = io.getcwd()
    last, directory = None, io.abspath(directory)
    while directory != last:
        path = io.join(directory, filename)
        if io.exists(path):
            return path
        last, directory = directory, io.dirname(directory)
    return None

def load_config_file(filename, io):
    if filename is None:
        config = {}
    else:
        if not io.isfile(filename):
            raise FilesystemError("not a file: {}".format(filename))
        try:
            with io.open(filename) as f:
                config = json.load(f)
        except OSError as e:
            raise FilesystemError("could not read file {}: {}"
                                  .format(repr(filename), str(e)))
        except json.decoder.JSONDecodeError as e:
            raise UserDataError("malformed JSON in {}: {}"
                                .format(repr(filename), str(e)))
    if not isinstance(config, dict):
        raise UserDataError("config file is not map")
    if "aliases" in config:
        if not isinstance(config, dict):
            raise UserDataError("value of 'aliases' is not map")
        for key, val in config["aliases"].items():
            if not isinstance(key, str):
                raise UserDataError("alias name {} is not string"
                                    .format(key))
            if not isinstance(val, str):
                raise UserDataError("alias value {} is not string"
                                    .format(val))
    else:
        config["aliases"] = {}
    return config

## Command line

SUBCOMMANDS = {
    "init": subcommand_init,
    "import": subcommand_import,
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
        commands = [args]
        subcommand, *args = args
        if subcommand in ("help", "-h", "-help", "--help", "-?"):
            io.print_usage(stream=io.stdout)
        else:
            config_file = locate_dominating_file("config.json", io)
            config = load_config_file(config_file, io)
            seen_aliases = set()
            try:
                while subcommand in config["aliases"]:
                    if subcommand in seen_aliases:
                        if subcommand in SUBCOMMANDS:
                            break
                        else:
                            raise RawUsageError(
                                "alias {} expands to itself".format(repr(subcommand)))
                    alias_args = shlex.split(config["aliases"][subcommand])
                    args = alias_args + args
                    if not args:
                        raise RawUsageError(
                            "usage of alias {} expands to empty command"
                            .format(repr(subcommand)))
                    seen_aliases.add(subcommand)
                    commands.append(args)
                    subcommand, *args = args
                if subcommand in SUBCOMMANDS:
                    try:
                        SUBCOMMANDS[subcommand](args, io)
                    except UsageError as e:
                        raise UsageError(subcommand + " " + str(e))
                else:
                    raise RawUsageError("no such command or alias: {}"
                                        .format(subcommand))
            except Failure as e:
                if len(commands) > 1:
                    for command in commands:
                        io.print("> " + quote_command(command), stream=io.stderr)
                    io.print(stream=io.stderr)
                raise
    except UsageError as e:
        io.print_usage(str(e))
        return 1
    except Failure as e:
        io.print_error(str(e))
        return 1
    except Success:
        pass
    return 0
