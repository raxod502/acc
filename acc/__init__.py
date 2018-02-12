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

class UsageError(Failure):
    pass

class StandardUsageError(Failure):
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

TOPLEVEL_USAGE = """[-C <dir>] <subcommand> [<arg>...]"""

SUBCOMMAND_USAGE = {
    "init": "[--git | --no-git] [--] <dir>",
    "import": "<importer> [<arg>...]",
    "merge": "[--append-only | --no-append-only] [--] <source-ledger> <target-ledger>",
}

SUBCOMMANDS = ["init", "import", "merge"]

assert len(SUBCOMMANDS) == len(set(SUBCOMMANDS))
assert set(SUBCOMMANDS) == set(SUBCOMMAND_USAGE.keys())

def usage(subcommand=None, config=None, config_error=None):
    if subcommand is None:
        message = TOPLEVEL_USAGE
        message += "\n\nAvailable subcommands:"
        for subcommand in SUBCOMMANDS:
            message += "\n    {} {}".format(
                subcommand, SUBCOMMAND_USAGE[subcommand])
        message += "\n    help"
        if config:
            message += "\n\nDefined aliases:"
            for alias in sorted(config["aliases"]):
                message += "\n    " + alias
        if config_error:
            message += "\n\nError while loading config file:\n    "
            message += str(config_error)
        return message
    else:
        return SUBCOMMAND_USAGE[subcommand]

def usage_error(*args, **kwargs):
    return StandardUsageError(usage(*args, **kwargs))

## IOWrapper

class IOWrapper:
    def __init__(self, io, exec_name):
        self.io = io
        self.exec_name = exec_name

    def print(self, *args, stream=None, **kwargs):
        if stream is None:
            stream = self.io.stdout
        print(*args, file=stream, **kwargs)

    def print_stderr(self, *args, **kwargs):
        print(*args, file=self.io.stderr, **kwargs)

    def print_error(self, text):
        message = "{}: {}".format(self.exec_name, text)
        self.print_stderr(message)

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
                    date = datetime.datetime.strptime(date, DATETIME_FORMAT)
                else:
                    date = datetime.datetime.strptime(date, DATE_FORMAT).date()
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
        raise usage_error("init")
    if path is None:
        raise usage_error("init")
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
    config = load_config_file(None, io)
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
        message = SUBCOMMAND_USAGE["import"] + format_importer_list()
        raise StandardUsageError(message)
    importer_name, *args = args
    module_name = "acc.importers.{}".format(importer_name)
    if not importlib.util.find_spec(module_name):
        message = "no such module: {}{}".format(
            module_name, format_importer_list())
        raise FilesystemError(message)
    importer = importlib.import_module(module_name)
    try:
        importer.run(args, io)
    except StandardUsageError as e:
        raise StandardUsageError(importer_name + " " + str(e))

### merge

def transaction_similarity(t1, t2):
    similarity = 0
    keys = set(t1.keys()) | set(t2.keys())
    for key in keys:
        if t1.get(key) != t2.get(key):
            similarity -= 1
    return similarity

def most_similar_transaction(transaction, transactions):
    return max(filter(lambda t: t is not transactions, transactions),
               key=lambda t: transaction_similarity(t, transaction))

def subcommand_merge(args, io):
    source_file = None
    target_file = None
    args_done = False
    for arg in args:
        if not args_done:
            if arg == "--":
                args_done = True
                continue
        if source_file is None:
            source_file = arg
            continue
        if target_file is None:
            target_file = arg
            continue
        raise usage_error("merge")
    if source_file is None or target_file is None:
        raise usage_error("merge")
    if not io.isfile(source_file):
        raise FilesystemError("no such file: {}".format(source_file))
    try:
        with open(source_file) as f:
            source_ledger = f.read()
    except OSError as e:
        raise FilesystemError("could not read file {}: {}"
                              .format(repr(source_file, str(e))))
    try:
        source_ledger = deserialize_ledger(source_ledger)
    except Failure as e:
        raise type(e)("in file {}: {}".format(repr(source_file), str(e)))
    if io.isfile(target_file):
        try:
            with open(target_file) as f:
                target_ledger = f.read()
        except OSError as e:
            raise FilesystemError("could not read file {}: {}"
                                  .format(repr(target_file, str(e))))
        try:
            target_ledger = deserialize_ledger(target_ledger)
        except Failure as e:
            raise type(e)("in file {}: {}".format(repr(target_file), str(e)))
    else:
        target_ledger = None
    if target_ledger is None:
        merged_ledger = source_ledger
    else:
        raise NotImplementedError # FIXME
    ledger_str = serialize_ledger(merged_ledger)
    target_dir = io.dirname(io.abspath(target_file))
    try:
        io.makedirs(target_dir, exist_ok=True)
    except OSError as e:
        raise FilesystemError(
            "could not create directory {}: {}"
            .format(repr(target_dir), str(e)))
    try:
        with io.open(target_file, "w") as f:
            f.write(ledger_str)
            f.write("\n")
    except OSError as e:
        raise FilesystemError(
            "could not write file {}: {}"
            .format(repr(target_file), str(e)))

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
    "merge": subcommand_merge,
}

def command_line(exec_name, args, io):
    io = IOWrapper(io, exec_name)
    try:
        while args and args[0] == "-C":
            if len(args) == 1:
                raise usage_error()
            path = args[1]
            if not io.isdir(path):
                raise FilesystemError("no such directory: {}".format(path))
            io.chdir(path)
            args = args[2:]
        try:
            config_file = locate_dominating_file("config.json", io)
            config = load_config_file(config_file, io)
            config_or_none = config if config_file is not None else None
            config_error = None
        except Failure as e:
            config = config_or_none = None
            config_error = e
        if not args:
            raise usage_error(config=config_or_none, config_error=config_error)
        commands = [args]
        subcommand, *args = args
        if subcommand in ("help", "-h", "-help", "--help", "-?"):
            message = usage(config=config, config_error=config_error)
            io.print("usage: " + io.exec_name + " " + message)
        elif config_error:
            raise config_error
        else:
            seen_aliases = set()
            try:
                while subcommand in config["aliases"]:
                    if subcommand in seen_aliases:
                        if subcommand in SUBCOMMANDS:
                            break
                        else:
                            raise UsageError(
                                "alias {} expands to itself".format(repr(subcommand)))
                    alias_args = shlex.split(config["aliases"][subcommand])
                    args = alias_args + args
                    if not args:
                        raise UsageError(
                            "usage of alias {} expands to empty command"
                            .format(repr(subcommand)))
                    seen_aliases.add(subcommand)
                    commands.append(args)
                    subcommand, *args = args
                if subcommand in SUBCOMMANDS:
                    try:
                        SUBCOMMANDS[subcommand](args, io)
                    except StandardUsageError as e:
                        raise StandardUsageError(subcommand + " " + str(e))
                else:
                    raise UsageError("no such command or alias: {}"
                                     .format(subcommand))
            except Failure as e:
                if len(commands) > 1:
                    for command in commands:
                        io.print_stderr("> " + quote_command(command))
                    io.print_stderr()
                raise
    except StandardUsageError as e:
        io.print_stderr("usage: " + io.exec_name + " " + str(e))
        return 1
    except Failure as e:
        io.print_error(str(e))
        return 1
    except Success:
        pass
    return 0
