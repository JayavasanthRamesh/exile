import log
import os

class FileMapping:
    """Provides convenience methods for accessing and manipulating the JSON config object."""

    def __init__(self, root, config, silent=False):
        """
        Args:
            root: the directory containing the config file; the root of the exile context
            config: the parsed representation of the file configuration
            silent: if true, no messages will be printed
        """
        self.__root = root
        self.__config = config
        self.__silent = silent

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
            if not self.__silent:
                log.info("skipping path outside manifest scope: " + path)
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
            if not self.__silent:
                log.warning("path is not tracked: " + path)
            return []

        # paths in "parts" are relative to the repo root, but we want absolute paths
        absolute = os.path.realpath(os.path.join(os.path.relpath(self.__root), *parts))
        return self.__paths(absolute, value)

    def add(self, path, hash, silent=False):
        """
        Add the given path to the configuration.

        Args:
            path: the path to the file to add
            hash: the hash of the file
            silent: if True, this operation will not emit any messages
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
                
                if changed and not (self.__silent or silent):
                    log.message("adding: " + os.path.join(*parts))

                return changed

            if parts[i] not in dict:
                dict[parts[i]] = {}
                changed = True

            dict = dict[parts[i]]

        return False    # shouldn't get here

    def remove(self, path):
        """
        Remove all tracked files under a given path and return a FileMapping containing the removed elements.

        For example given the following files (relative to the root for simplicity):
        a
        b/c/d
        b/c/e
        b/f

        Calling remove with path = 'b/c' would return a mapping containing:
        {
            "b": {
                "c": {
                    "d": "<somehash>",
                    "e": "<somehash>"
                }
            }
        }

        Args:
            path: the path to recursively remove
        """

        parts = self.__path_components(path)
        if len(parts) > 0:
            removed = {}
            current = removed
            for part in parts[:-1]:
                current[part] = {}
                current = current[part]

            parent = self.__get(parts[:-1])
            last_part = parts[-1]
            try:
                leaf = parent[last_part]
            except KeyError:
                return None   # if its already missing, no problem
            current[last_part] = leaf
            del parent[last_part]

            return FileMapping(self.__root, removed, True)

        return None