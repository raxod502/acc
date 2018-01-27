import acc

import os
import sys

class IO:
    def __init__(self):
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.chdir = os.chdir
        self.isdir = os.path.isdir

if __name__ == "__main__":
    program_name = "acc"
    args = sys.argv[1:]
    sys.exit(acc.command_line(program_name, args, IO()))
