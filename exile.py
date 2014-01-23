#!/usr/bin/env python

import json
import imp
import hashlib
import os
import shutil
import argparse
import sys

MANIFEST_NAME = "exile.manifest"
CACHE_DIR = ".exile.cache"

def info(msg):
    if args.verbosity >= 3:
        print "info: " + msg

def warning(msg):
    if args.verbosity >= 2:
        print "warning: " + msg

def message(msg):
    if args.verbosity >= 1:
        print msg

def error(msg):
    print "error: " + msg
    sys.exit(1)

class CachedCommunicator:
    """Wrapper around the Communicator classes provided by adapters, but maintains a local cache."""

    def __init__(self, cache_path, communicator):
        if os.path.exists(cache_path):
            if not os.path.isdir(cache_path):
                raise RuntimeError('cache is not a directory, please remove it: ' + cache_path)
        else:
            os.mkdir(cache_path)

        self.__cache = cache_path
        self.__comm = communicator

    def get(self, hash, dest):
        """
        Copies an object from the cache to a destination, downloading it if necessary.

        Args:
            hash: the name of the object (the hash of the file)
            dest: the path to which the object should be copied
        """

        cached = os.path.join(self.__cache, hash)

        if not os.path.exists(cached):
            self.__comm.get(hash, cached)

        if not os.path.exists(cached):
            raise RuntimeError("failed to download object: " + hash)

        if not os.path.isfile(cached):
            raise RuntimeError("stray non-file object in cache, please remove: " + cached)

        dir = os.path.dirname(dest)
        if dir and not os.path.exists(dir):
            os.makedirs(os.path.dirname(dest))
        shutil.copy(cached, dest)

    def put(self, source, hash):
        """
        Uploads an object to the remote, keeping a copy in the local cache.

        Args:
            source: the file to upload
            hash: the name of the object to create (the hash of the file)
        """

        shutil.copy(source, os.path.join(self.__cache, hash))
        self.__comm.put(source, hash)

class FileMapping:
    """Provides convenience methods for accessing and manipulating the JSON config object."""

    def __init__(self, root, config):
        """
        Args:
            root: the path to the config file; the root of the exile context
            config: the parsed representation of the file configuration
        """
        self.__root = root
        self.__config = config

    def __path_components(self, path):
        """
        Splits a path into a list of path components relative to the configuration file.

        For example, if the manifest file was at /tmp/exile.manifest:

            /tmp/path/to/a/file

        becomes:

            ['path', 'to', 'a', 'file']
        """

        path = os.path.realpath(path)
        if not path.startswith(self.__root):
            info("skipping path outside manifest scope: " + path)
            return None

        relative = os.path.relpath(path, self.__root)

        parts = []
        head, tail = os.path.split(relative)
        while tail:
            parts = [tail] + parts
            head, tail = os.path.split(head)

        if head:
            parts = [head] + parts

        return parts

    def __get(self, parts):
        """
        Get the value from the file configuration for a path. If the path represents a directory,
        the return value with be a dict. If it is a file, the result will be a string (the configured
        hash for that path).

        Args:
            parts: a list of componenets of the path (probably from __path_components)
        """
        try:
            value = self.__config
            for part in parts:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return None

    def get(self, path):
        """
        Gets the configured object for a given path. If the path is not a file
        or is not tracked, returns None.
        """

        value = self.__get(self.__path_components(path))
        if type(value) is dict:
            return None
        return value

    def __paths(self, parent, value):
        """
        Recursive helper for building a a path list. See "paths".

        Args:
            parent: the path to the subtree represented by value
            value: the subtree of the file configuration corresponding to the above path
        """

        paths = []
        if type(value) is dict:
            for k, v in value.iteritems():
                paths += self.__paths(os.path.join(parent, k), v)
        else:
            paths.append(parent)

        return paths

    def paths(self, path):
        """
        Given a path, returns the list of tracked files that fall under that path.

        For example, "/tmp/test" may return ["/tmp/test/a", "/tmp/test/b"].
        """

        parts = self.__path_components(path)
        value = self.__get(parts)
        if value is None:
            warning("path is not tracked: " + path)
            return []

        return self.__paths(os.path.join(*parts), value)

    def add(self, path, hash):
        """
        Add the given path to the configuration.

        Args:
            path: the path to the file to add
            hash: the hash of the file
        """

        parts = self.__path_components(path)
        if not parts:
            return False

        changed = False
        dict = self.__config
        for i in range(len(parts)):
            if i is len(parts) - 1:
                if parts[i] not in dict or dict[parts[i]] != hash:
                    dict[parts[i]] = hash
                    changed = True
                
                if changed:
                    message("adding: " + os.path.join(*parts))

                return changed

            if parts[i] not in dict:
                dict[parts[i]] = {}
                changed = True

            dict = dict[parts[i]]

        return False    # shouldn't get here

def hash(path):
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

def create_communicator(config):
    """Factory for communicator objects based on the configured type."""

    type = config['type']

    # finds the module (python file) with the same name as the specified type in the "adapters" directory and loads it
    file, path, desc = imp.find_module(type, [os.path.join(os.path.dirname(os.path.realpath(__file__)), 'adapters')])
    comm_module = imp.load_module(type, file, path, desc)

    return comm_module.Communicator(config)

arg_parser = argparse.ArgumentParser(description="Add and resolve files stored in an exile repository.",
                                     formatter_class=argparse.RawTextHelpFormatter)
arg_parser.add_argument("action", choices=['resolve', 'add', 'clean'],
                        help="the action to perform\n  resolve copy paths from the repository\n  add     add new paths to the repository\n  clean   delete locally cached objects")
arg_parser.add_argument("paths", nargs='*',
                        help="the paths to which the action applies")
arg_parser.add_argument("-v", "--verbosity", type=int, default=2,
                        help="the amount of informational output to produce\n  0: only errors\n  1: + normal output\n  2: + warnings (default)\n  3: + informational notes")
args = arg_parser.parse_args()

try:
    # load an parse configuration file
    config_path = find_config()
    with open(config_path, 'r') as file:
        config = json.load(file)

    # compute location of cache and create communicator
    cache_path = os.path.join(os.path.dirname(config_path), CACHE_DIR)
    comm = CachedCommunicator(cache_path, create_communicator(config['remote']))
except Exception as e:
    error(str(e))

# insert an empty dict for config files without any tracked files
if 'files' not in config
    config['files'] = {}

filemap = FileMapping(os.path.dirname(config_path), config['files'])

def resolve(paths):
    """
    Download files from a remote and place them in their configured locations.

    Args:
        paths: a list of paths to add. Directories will be resolved recursively.
    """
    for path in paths:
        for relative in filemap.paths(path):
            message("resolving: " + relative)
            filehash = filemap.get(relative)
            comm.get(filehash, relative)

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
            warning("path does not exist: " + path)
                

    # update the config file
    with open(config_path, 'w') as file:
        json.dump(config, file, indent=4, sort_keys=True)

def clean(ignored):
    """Removes locally cached objects."""
    shutil.rmtree(cache_path)

try:
    # calls the local function with the same name as the action argument -- "add" calls add(paths)
    locals()[args.action](args.paths)
except Exception as e:
    error(str(e))