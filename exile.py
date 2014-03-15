#!/usr/bin/env python

import argparse
import exile
import hashlib
import imp
import json
import os
import shutil
import sys
import time

MANIFEST_NAME = "exile.manifest"
CACHE_DIR = "exile.cache"

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

def find_cache(root, config):
    """
    Determines the approriate location for the local object cache

    Args:
        root: the path to the directory containing the config file
        config: the parsed configuration
    """

    cache_path = config['remote'].get('cache', None)
    # if no user-specified directory, find a reasonable place
    if cache_path is None:
        # default to the directory of the manifest
        cache_path = os.path.join(root, "." + CACHE_DIR)
        try:
            # on systems with conventions around temp directories, try those
            if os.name == 'posix':
                cache_path = os.path.join(os.environ['TMPDIR'], CACHE_DIR)
            elif sys.platform == 'win32':
                cache_path = os.path.join(os.environ['TEMP'], CACHE_DIR)
        except KeyError:
            pass
    else:
        # resolves any relative paths against the root
        if not os.path.isabs(cache_path):
            cache_path = os.path.realpath(os.path.join(root, cache_path))

    return cache_path

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

def cache(args):
    snapshot_path = os.path.realpath(exile.remote.SNAPSHOT)

    if args.cache_action == 'clean':
        if args.objects:
            exile.log.message("Cleaning object cache at " + cache_path)
            try:
                shutil.rmtree(cache_path)
            except OSError:
                pass

        if args.snapshot:
            exile.log.message("Cleaning snapshot file " + snapshot_path)
            try:
                os.remove(snapshot_path)
            except OSError:
                pass
            
    elif args.cache_action == 'info':
        exile.log.message("Object cache: " + cache_path)

        try:
            exile.log.message("Snapshot file (updated %s): %s" % (time.ctime(os.path.getmtime(snapshot_path)), snapshot_path))
        except os.error:
            exile.log.message("No snapshot file")

    sys.exit(0)


root_parser = argparse.ArgumentParser(description="Add and resolve files stored in an exile repository.",
                                     formatter_class=argparse.RawTextHelpFormatter)
root_parser.add_argument("-v", "--verbosity", type=int, default=2,
                        help="the amount of informational output to produce\n  0: only errors\n  1: + normal output\n  2: + warnings (default)\n  3: + informational notes")
subparsers = root_parser.add_subparsers(dest='action')

resolve_parser = subparsers.add_parser('resolve', help='copy paths from the repository')
resolve_parser.add_argument("paths", nargs='*',
                            help="the paths to which the action applies")
resolve_parser.add_argument("-f", "--force", action='store_true',
                            help="forces resolution of all matching files, even if exile thinks they are already up-to-date")

add_parser = subparsers.add_parser('add', help='add new paths to the repository')
add_parser.add_argument("paths", nargs='*',
                        help="the paths to which the action applies")

init_parser = subparsers.add_parser('init', help='create a new manifest in the current directory')
init_parser.add_argument("-t", "--type",
                         help="specifies the type of remote to configure")

cache_parser = subparsers.add_parser('cache', help='manipulate exile\'s caches')
cache_subparsers = cache_parser.add_subparsers(dest='cache_action')
cache_clean_parser = cache_subparsers.add_parser('clean', help='purge all caches (customizeable with options)')
cache_clean_parser.add_argument("-s", "--snapshot", action='store_true',
                                help='remove the local snapshot (cache of working tree state)')
cache_clean_parser.add_argument("-o", "--objects", action='store_true',
                                help='clean all cached objects (possibly shared by other exile repositories)')
cache_info_parser = cache_subparsers.add_parser('info', help='display information about the caches')

args = root_parser.parse_args()

exile.log.verbosity = args.verbosity

if args.action == 'init':
    init(args.type)
    sys.exit(0)

try:
    # load an parse configuration file
    config_path = find_config()
    with open(config_path, 'r') as file:
        config = json.load(file)

    # compute location of cache and create communicator
    cache_path = find_cache(os.path.dirname(config_path), config)
    
    if args.action == 'cache':
        cache(args)

    comm = exile.worker.AsyncCommunicator(os.path.dirname(config_path), cache_path, config['remote'], getattr(args, 'force', False))
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

try:
    # calls the local function with the same name as the action argument -- "add" calls add(paths)
    locals()[args.action](args.paths)
except Exception as e:
    exile.log.error(str(e))
