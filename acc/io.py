import os
import shutil
import subprocess
import sys

class StandardIO:
    def __init__(self):
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.chdir = os.chdir
        self.isdir = os.path.isdir
        self.dirname = os.path.dirname
        self.abspath = os.path.abspath
        self.islink = os.path.islink
        self.exists = os.path.exists
        self.which = shutil.which
        self.mkdir = os.mkdir
        self.run = subprocess.run
        self.join = os.path.join
        self.makedirs = os.makedirs
        self.open = open
        self.getcwd = os.getcwd
        self.isfile = os.path.isfile
        self.DEVNULL = subprocess.DEVNULL
