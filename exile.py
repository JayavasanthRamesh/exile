#!/usr/bin/env python

import argparse
import exile
import hashlib
import imp
import json
import os
import shutil
import sys

MANIFEST_NAME = "exile.manifest"
CACHE_DIR = ".exile.cache"

def hash(path):
    """Compute the SHA1 hash of a file"""

    with open(path, 'r') as file:
        return hashlib.sha1(file.read()).hexdigest()

def find_config():
    """Looks for a config file at or above the current directory."""

    curr = os.getcwd()
    while not os.path.isfile(os.path.join(curr, MANIFEST_NAME)):
        next = os.path.dirname(curr)

        # if at root, stop
        if next == curr:
            raise RuntimeError("no '%s' file found in any parent directory"%(MANIFEST_NAME))
        
        curr = next

    return os.path.join(curr, MANIFEST_NAME)

def init(type):
    """
    Create a blank manifest in the current directory populated with the template configuration for the specified remote type.

    Args:
        type: the remote type to initialize (must exist in adapters/)
    """

    if type is None:
        exile.log.error("no remote type specified (use -t)")

    # should throw exception
    try:
        exile.log.error("manifest already exists: " + find_config())
    except RuntimeError as e:
        pass

    try:
        file, path, desc = imp.find_module(type, [os.path.join(os.path.dirname(os.path.realpath(__file__)), 'adapters')])
        comm_module = imp.load_module(type, file, path, desc)
    except ImportError as e:
        exile.log.error("no adapter for remote type: " + type)

    template = getattr(comm_module, 'template', {})
    if not hasattr(template, 'type'):
        template['type'] = type

    config = { "remote": template }
    with open('exile.manifest', 'w') as file:
        json.dump(config, file, indent=4, sort_keys=True)

    exile.log.message("Initialized manifest with remote type '%s'" % (args.type))


arg_parser = argparse.ArgumentParser(description="Add and resolve files stored in an exile repository.",
                                     formatter_class=argparse.RawTextHelpFormatter)
arg_parser.add_argument("action", choices=['resolve', 'add', 'clean', 'init'],
                        help="the action to perform\n  init    create a new manifest in the current directory\n  resolve copy paths from the repository\n  add     add new paths to the repository\n  clean   delete locally cached objects")
arg_parser.add_argument("paths", nargs='*',
                        help="the paths to which the action applies")
arg_parser.add_argument("-t", "--type",
                        help="when used with 'init', specifies the type of remote to configure")
arg_parser.add_argument("-v", "--verbosity", type=int, default=2,
                        help="the amount of informational output to produce\n  0: only errors\n  1: + normal output\n  2: + warnings (default)\n  3: + informational notes")
args = arg_parser.parse_args()

exile.log.verbosity = args.verbosity

if args.action == "init":
    init(args.type)
    sys.exit(0)

try:
    # load an parse configuration file
    config_path = find_config()
    with open(config_path, 'r') as file:
        config = json.load(file)

    # compute location of cache and create communicator
    cache_path = os.path.join(os.path.dirname(config_path), CACHE_DIR)
    comm = exile.worker.AsyncCommunicator(cache_path, config['remote'])
except Exception as e:
    exile.log.error(str(e))

# insert an empty dict for config files without any tracked files
if 'files' not in config:
    config['files'] = {}

filemap = exile.files.FileMapping(os.path.dirname(config_path), config['files'])

def resolve(paths):
    """
    Download files from a remote and place them in their configured locations.

    Args:
        paths: a list of paths to add. Directories will be resolved recursively.
    """
    for path in paths:
        for relative in filemap.paths(path):
            exile.log.message("resolving: " + relative)
            filehash = filemap.get(relative)
            comm.get(filehash, relative)

    comm.join()

def add_file(path):
    """
    Add a single file. This only changes the parsed configuration, not the file.

    Args:
        path: the path to a file to add (must be a file)
    """
    filehash = hash(path)
    if filemap.add(path, filehash):
        comm.put(path, filehash)

def add(paths):
    """
    Start tracking a file. This includes uploading the object and updating the configuration file.

    Args:
        paths: a list of paths to add. Directories will be added recursively.
    """
    cwd = os.getcwd()

    for path in paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        add_file(os.path.join(root, file))
            elif os.path.isfile(path):
                add_file(path)
        else:
            exile.log.warning("path does not exist: " + path)
                
    comm.join()

    # update the manifest file
    with open(config_path, 'w') as file:
        json.dump(config, file, indent=4, sort_keys=True)

def clean(ignored):
    """Removes locally cached objects."""

    shutil.rmtree(cache_path)
    exile.log.message("cache cleaned")

try:
    # calls the local function with the same name as the action argument -- "add" calls add(paths)
    locals()[args.action](args.paths)
except Exception as e:
    exile.log.error(str(e))
