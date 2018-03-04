import acc.importers

import copy
import datetime
import importlib
import json
import pkgutil
import random
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

TOPLEVEL_USAGE = "[-C <dir>] [--git | --no-git] [--] <subcommand> [<arg>...]"

SUBCOMMAND_USAGE = {
    "init": "<dir>",
    "import": "<importer> [<arg>...]",
    "merge": "[--require-overlap | --no-require-overlap] [--] <source-ledger> <target-ledger>",
    "balance": "[<primary-name>=]<primary-ledger> [<secondary-name>=]<secondary-ledger>",
}

SUBCOMMANDS = ("init", "import", "merge", "balance")

SUBCOMMANDS_USING_GIT = {"import", "merge", "balance"}
SUBCOMMANDS_REQUESTING_GIT = {"init"}

# No duplicates in subcommand list.
assert len(SUBCOMMANDS) == len(set(SUBCOMMANDS))

# Usage given for each subcommand.
assert set(SUBCOMMANDS) == set(SUBCOMMAND_USAGE)

# Special subcommands are limited to existing ones.
assert SUBCOMMANDS_USING_GIT <= set(SUBCOMMANDS)
assert SUBCOMMANDS_REQUESTING_GIT <= set(SUBCOMMANDS)

# No overlap between categories of special subcommands.
assert not (SUBCOMMANDS_USING_GIT & SUBCOMMANDS_REQUESTING_GIT)

def usage(subcommand=None, config=None, config_error=None):
    if subcommand is None:
        message = TOPLEVEL_USAGE
        message += "\n\nAvailable subcommands:"
        for subcommand in SUBCOMMANDS:
            message += "\n    {} {}".format(
                subcommand, SUBCOMMAND_USAGE[subcommand])
        message += "\n    help"
        if config and config["aliases"]:
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

## Utilities
### Strings

class Placeholder:

    def __init__(self, contents):
        self.contents = contents

    def __repr__(self):
        return self.contents

def quote_command(args):
    return " ".join(shlex.quote(arg) for arg in args)

### Miscellaneous

def random_transaction_id():
    return str(uuid.uuid4())

## Git integration

def is_working_tree_clean(io):
    try:
        # Make sure working tree matches HEAD.
        result = io.run(["git", "diff-files", "--quiet"])
        if result.returncode != 0:
            return False
        # Make sure index matches HEAD.
        result = io.run(["git", "diff-index", "--cached", "--quiet", "HEAD"])
        if result.returncode != 0:
            return False
        # Make sure there are no untracked files.
        result = io.run(["git", "ls-files", "--others", "--exclude-standard"],
                        stdout=io.PIPE)
        if result.returncode != 0:
            raise ExternalCommandError(
                "command failed: {}".format(quote_command(result.args)))
        if result.stdout:
            return False
        return True
    except OSError as e:
        raise ExternalCommandError(
            "unexpected failure while running 'git': {}"
            .format(str(e)))

def ensure_working_tree_clean(io):
    if not io.which("git"):
        return
    if not is_working_tree_clean(io):
        try:
            io.run(["git", "status"])
        except OSError as e:
            raise ExternalCommandError(
                "unexpected failure while running 'git': {}"
                .format(str(e)))
        raise FilesystemError("working directory is not clean")

def commit_working_tree(io, message):
    if not io.which("git"):
        return
    try:
        if io.run(["git", "add", "-A"]).returncode != 0:
            raise OSError("command failed: git add -A")
        if not is_working_tree_clean(io):
            if io.run(["git", "commit", "-m", message]).returncode != 0:
                raise OSError("command failed: git commit -m {}"
                              .format(shlex.quote(message)))
    except OSError as e:
        raise ExternalCommandError(
            "unexpected failure while running 'git': {}"
            .format(str(e)))

## Transactions and ledgers

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"

def is_datetime(date):
    return ":" in date

def format_date(date):
    if isinstance(date, datetime.date):
        return date.strftime(DATE_FORMAT)
    elif isinstance(date, datetime.datetime):
        return date.strftime(DATETIME_FORMAT)
    else:
        raise InternalError(
            "cannot serialize date of type {}: {}"
            .format(repr(type(date)), repr(date)))

def parse_date(date):
    try:
        if is_datetime(date):
            return datetime.datetime.strptime(date, DATETIME_FORMAT)
        else:
            return datetime.datetime.strptime(date, DATE_FORMAT).date()
    except ValueError:
        raise UserDataError("malformed date: {}".format(date))

def transaction_delta(transaction, account):
    value = transaction["value"]
    if transaction["type"] == "credit":
        return value
    elif transaction["type"] == "debit":
        return -value
    elif transaction["type"] == "transfer":
        if transaction["source-account"] == account:
            return -value
        elif transaction["target-account"] == account:
            return value
        else:
            return 0
    else:
        raise InternalError(
            "unexpected transaction type: {}"
            .format(repr(transaction["type"])))

def serialize_ledger(ledger):
    transactions = []
    for transaction in ledger["transactions"]:
        transaction = dict(transaction)
        if "date" in transaction:
            transaction["date"] = format_date(transaction["date"])
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
            transaction["date"] = parse_date(transaction["date"])
    return ledger

def read_ledger_file(filename):
    try:
        with open(filename) as f:
            ledger = f.read()
    except OSError as e:
        raise FilesystemError("could not read file {}: {}"
                              .format(repr(filename), str(e)))
    try:
        ledger = deserialize_ledger(ledger)
    except Failure as e:
        raise type(e)("in file {}: {}".format(repr(filename), str(e)))

## Subcommands
### init

def subcommand_init(args, io, using_git, **kwargs):
    if len(args) != 1:
        raise usage_error("init")
    path = args[0]
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
    if using_git:
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

def subcommand_import(args, io, **kwargs):
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

def transactions_equivalent(t1, t2):
    t1_norm, t2_norm = dict(t1), dict(t2)
    del t1_norm["id"]
    del t2_norm["id"]
    return t1_norm == t2_norm

UNSET = Placeholder("(unset)")

def diff_maps(m1, m2, exclude_keys=[]):
    for key in set(m1) | set(m2):
        if key in exclude_keys:
            continue
        v1, v2 = m1.get(key, UNSET), m2.get(key, UNSET)
        if v1 != v2:
            return ("have differing values for key {}: respectively {} and {}"
                    .format(repr(key), repr(v1), repr(v2)))
    return None

def merge_ledgers(source_ledger, target_ledger, require_overlap):

    # If target ledger does not exist, just copy the source ledger.
    if target_ledger is None:
        return source_ledger

    # Extract substructures.
    source_metadata = source_ledger["metadata"]
    target_metadata = target_ledger["metadata"]
    source_transactions = source_ledger["transactions"]
    target_transactions = target_ledger["transactions"]

    # Ensure that metadata matches.
    metadata_diff = diff_maps(source_metadata, target_metadata)
    if metadata_diff:
        raise UserDataError("source and target ledger metadata {}"
                            .format(metadata_diff))

    # If no transactions in target ledger, just copy the source ledger.
    if not target_transactions:
        return source_ledger

    # If no transactions in source ledger, don't modify the target ledger.
    if not source_transactions:
        return target_ledger

    # Get the location of the first transaction from the source ledger
    # within the target ledger.
    base_transaction = source_transactions[0]
    found_alignment = False
    for target_idx, target_transaction in enumerate(target_transactions):
        if transactions_equivalent(base_transaction, target_transaction):
            found_alignment = True
            break

    if require_overlap:
        # If no alignment, report an error.
        if not found_alignment:
            most_similar = most_similar_transaction(
                base_transaction, target_transactions)
            most_similar_diff = diff_maps(base_transaction, most_similar)
            assert most_similar_diff
            raise UserDataError(
                ("first transaction in source ({}) and most similar "
                 "transaction in target ledger ({}) {}")
                .format(repr(base_transaction["id"]),
                        repr(most_similar["id"]),
                        most_similar_diff))

        # Ensure alignment continues.
        for source_transaction, target_transaction in zip(
                source_transactions, target_transactions[target_idx:]):
            align_diff = diff_maps(
                source_transaction, target_transaction, exclude_keys=["id"])
            if align_diff:
                raise UserDataError(
                    ("ledgers do not align; transactions in source "
                     "({}) and target ({}) {}")
                    .format(repr(source_transaction["id"]),
                            repr(target_transaction["id"]),
                            align_diff))

    # Create merged ledger.
    #
    # Example of source_idx calculation:
    # [A, B, C, D, E] + [D, E, F]
    # target_idx = 3
    # source_idx = 2
    merged_ledger = copy.deepcopy(target_ledger)
    if found_alignment:
        source_idx = len(source_transactions) - target_idx
    else:
        source_idx = 0
    merged_ledger["transactions"].extend(source_ledger["transactions"][source_idx:])
    return merged_ledger

def subcommand_merge(args, io, **kwargs):
    source_file = None
    target_file = None
    require_overlap = True
    args_done = False
    for arg in args:
        if not args_done:
            if arg == "--":
                args_done = True
                continue
            if arg == "--require-overlap":
                require_overlap = True
                continue
            if arg == "--no-require-overlap":
                require_overlap = False
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
    source_ledger = read_ledger_file(source_file)
    if io.isfile(target_file):
        target_ledger = read_ledger_file(target_file)
    else:
        target_ledger = None
    merged_ledger = merge_ledgers(
        source_ledger, target_ledger, require_overlap)
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

### balance

def parse_ledger_name_and_file(arg, io):
    if "=" in arg:
        idx = arg.index("=")
        return arg[:idx], arg[idx+1:]
    else:
        return io.splitext(arg)[0], arg

def pad_strings(strings):
    length = max(len, strings)
    return ["{s: <{fill}}".format(s=s, fill=length) for s in strings]

def format_transactions(tids, max_length):
    transactions, ids = zip(*tids)
    deltas = ["${.2f}".format(transaction_delta(t)) for t in transactions]
    deltas = list(map(transaction_delta, transactions))
    dates = [format_date(t["date"]) for t in transactions]
    descriptions = [t.get("description", "(unknown)") for t in transactions]

    ids = pad_strings(ids)
    deltas = pad_strings(deltas)
    dates = pad_strings(dates)
    descriptions = pad_strings(descriptions)

    return ["{} ({}) {} - {}".format(delta, date, desc)[:max_length]
            for delta, date, desc in zip(deltas, dates, descriptions)]

def substitution_distance(s1, s2):
    d = 0
    for c1, c2 in zip(s1, s2):
        if c1 != c2:
            d += 1
    d += abs(len(s1) - len(s2))
    return d

def make_id(alphabet, length):
    new_id = ""
    for i in range(length):
        new_id += random.choice(alphabet)
    return new_id

def make_ids(alphabet, num):
    syms = len(alphabet)
    length = 1
    while True:
        max_num = (syms ** length) / (2 * (1 + length * (syms - 1)))
        if num < max_num:
            break
        length += 1
    ids = []
    while len(ids) < num:
        new_id = make_id(alphabet, length)
        ok = True
        for old_id in ids:
            if substitution_distance(old_id, new_id) < 2:
                ok = False
                break
        if ok:
            ids.append(new_id)
    return ids

def map_sectioned(groups, mapper):
    groups = list(groups)
    all_items = []
    for section, items in groups:
        all_items.extend(items)
    mapped_items = mapper(all_items)
    assert len(mapped_items) == len(all_items)
    count = 0
    for tup in groups:
        section, items = tup
        tup[1] = mapped_items[count:count+len(items)]
        count += len(items)
    return groups

def format_transaction_groups(left_groups, right_groups, width, height):
    def map_format(tids):
        return format_transactions(tids, width)
    left_groups = map_sectioned(left_groups, map_format)
    right_groups = map_sectioned(right_groups, map_format)

def subcommand_balance(args, io, **kwargs):
    if len(args) != 2:
        raise usage_error("balance")

    primary, secondary = args

    primary_name, primary_file = parse_ledger_name_and_file(primary, io)
    secondary_name, secondary_file = parse_ledger_name_and_file(secondary, io)

    primary_ledger = read_ledger_file(primary_file)
    secondary_ledger = read_ledger_file(secondary_file)

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
    "balance": subcommand_balance,
}

HELP_COMMANDS = ("help", "-h", "-help", "--help", "-?")

def command_line(exec_name, args, io):
    io = IOWrapper(io, exec_name)
    try:
        using_git = None
        while args:
            if args[0] in HELP_COMMANDS:
                # Try to read the config file, then print a usage
                # message further down.
                break
            if args[0] == "--":
                args = args[1:]
                break
            if not args[0].startswith("-"):
                break
            if args[0] == "-C":
                if len(args) == 1:
                    raise usage_error()
                path = args[1]
                if not io.isdir(path):
                    raise FilesystemError("no such directory: {}".format(path))
                io.chdir(path)
                args = args[2:]
                continue
            if args[0] == "--git":
                using_git = True
                args = args[1:]
                continue
            if args[0] == "--no-git":
                using_git = False
                args = args[1:]
                continue
            raise usage_error()
        original_args = args
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
        if subcommand in HELP_COMMANDS:
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
                                "alias {} expands to itself"
                                .format(repr(subcommand)))
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
                    if using_git is None:
                        if subcommand in SUBCOMMANDS_REQUESTING_GIT:
                            if not io.which("git"):
                                io.print_stderr(
                                    "hint: use --no-git to disable Git integration")
                                raise ExternalCommandError(
                                    "command not found: git")
                            using_git = True
                        elif subcommand in SUBCOMMANDS_USING_GIT:
                            if locate_dominating_file(".git", io):
                                result = io.run(
                                    ["git", "rev-parse", "--is-inside-work-tree"],
                                    stdout=io.PIPE)
                                if result.returncode != 0:
                                    raise ExternalCommandError(
                                        "command failed: {}"
                                        .format(quote_command(result.args)))
                                response = result.stdout.decode().strip()
                                if response != "true":
                                    raise ExternalCommandError(
                                        "unexpected response from command '{}': {}"
                                        .format(quote_command(result.args), response))
                                using_git = True
                            else:
                                using_git = False
                    if using_git and not io.which("git"):
                        raise ExternalCommandError("command not found: git")
                    try:
                        if using_git and subcommand in SUBCOMMANDS_USING_GIT:
                            ensure_working_tree_clean(io)
                        if (subcommand in SUBCOMMANDS_USING_GIT or
                            subcommand in SUBCOMMANDS_REQUESTING_GIT):
                            SUBCOMMANDS[subcommand](args, io, using_git=using_git)
                        else:
                            SUBCOMMANDS[subcommand](args, io)
                        if using_git and subcommand in SUBCOMMANDS_USING_GIT:
                            commit_working_tree(
                                io, quote_command(["acc"] + original_args))
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
