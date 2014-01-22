#!/usr/bin/env python

import json
import imp
import hashlib
import os
import shutil
import argparse

MANIFEST_NAME = "exile.manifest"
CACHE_DIR = ".exile.cache"

class ConfigurationError(Exception):
    pass

class CachedCommunicator:
    def __init__(self, cache_path, communicator):
        if os.path.exists(cache_path):
            if not os.path.isdir(cache_path):
                raise RuntimeError('cache is not a directory, please remove it: ' + cache_path)
        else:
            os.mkdir(cache_path)

        self.__cache = cache_path
        self.__comm = communicator

    def get(self, hash, dest):
        cached = os.path.join(self.__cache, hash)

        if not os.path.exists(cached):
            self.__comm.get(hash, cached)

        if not os.path.exists(cached):
            raise RuntimeError("failed to download object: " + hash)

        if not os.path.isfile(cached):
            raise RuntimeError("error: stray non-file object in cache, please remove: " + cached)

        if not os.path.exists(os.path.dirname(dest)):
            os.makedirs(os.path.dirname(dest))
        shutil.copy(cached, dest)

    def put(self, source, hash):
        shutil.copy(source, os.path.join(self.__cache, hash))
        self.__comm.put(source, hash)

class FileMapping:
    def __init__(self, root, config):
        self.__root = root
        self.__config = config

    def __path_components(self, path):
        path = os.path.realpath(path)
        if not path.startswith(self.__root):
            print "warning: skipping path not under manifest file: " + path
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
        try:
            value = self.__config
            for part in parts:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return None

    def has(self, path):
        return self.__get(self.__path_components(path)) is not None

    def __paths(self, parent, value):
        paths = []
        if type(value) is dict:
            for k, v in value.iteritems():
                paths += self.__paths(os.path.join(parent, k), v)
        else:
            paths.append(parent)

        return paths

    def get(self, path):
        value = self.__get(self.__path_components(path))
        if type(value) is dict:
            return None
        return value

    def paths(self, path):
        parts = self.__path_components(path)
        value = self.__get(parts)
        if value is None:
            print "warning: file is not tracked: " + path
            return []

        return self.__paths(os.path.join(*parts), value)

    def add(self, path, hash):
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
                    print "add: " + os.path.join(*parts)

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
    curr = os.getcwd()
    while not os.path.isfile(os.path.join(curr, MANIFEST_NAME)):
        next = os.path.dirname(curr)

        # if at root, stop
        if next == curr:
            raise ConfigurationError("no '%s' file found in any parent directory"%(MANIFEST_NAME))
        
        curr = next

    return os.path.join(curr, MANIFEST_NAME)

def create_communicator(config):
    type = config['type']

    file, path, desc = imp.find_module(type, [os.path.join(os.path.dirname(os.path.realpath(__file__)), 'adapters')])
    comm_module = imp.load_module(type, file, path, desc)

    return comm_module.Communicator(config)

arg_parser = argparse.ArgumentParser(description="Add and resolve files stored in an exile repository.",
                                     formatter_class=argparse.RawTextHelpFormatter)
arg_parser.add_argument("action", choices=['resolve', 'add', 'clean'],
                        help="the action to perform\n  resolve copy paths from the repository\n  add     add new paths to the repository\n  clean   delete locally cached objects")
arg_parser.add_argument("paths", nargs='*',
                        help="the paths to which the action applies")
args = arg_parser.parse_args()

config_path = find_config()
with open(config_path, 'r') as file:
    config = json.load(file)

cache_path = os.path.join(os.path.dirname(config_path), CACHE_DIR)
comm = CachedCommunicator(cache_path, create_communicator(config['remote']))

filemap = FileMapping(os.path.dirname(config_path), config['files'])

def resolve(paths):
    for path in paths:
        for relative in filemap.paths(path):
            print "resolve: " + relative
            filehash = filemap.get(relative)
            comm.get(filehash, relative)

def add_file(path):
    filehash = hash(path)
    if filemap.add(path, filehash):
        comm.put(path, filehash)

def add(paths):
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
            print "warning: path does not exist: " + path
                

    with open(config_path, 'w') as file:
        json.dump(config, file, indent=4, sort_keys=True)

def clean(ignored):
    shutil.rmtree(cache_path)

# resolve directory paths to a single list of files to process
locals()[args.action](args.paths)
