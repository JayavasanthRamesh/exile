import files
import json
import os
import shutil
import threading

SNAPSHOT = '.exile.snapshot'

# snapshot instance shared among all threads
# TODO: instance per-thread with merging logic
snapshot = None
snapshot_lock = threading.Lock()

class Snapshot:
    """Models the cached information about currently resolved files."""

    def __init__(self, root):
        self.__path = os.path.join(root, SNAPSHOT)

        try:
            with open(self.__path, 'r') as file:
                self.__data = json.load(file)
        except IOError as e:
            self.__data = {}

        self.__files = files.FileMapping(root, self.__data, silent=True)

    def getmtime(self):
        """Gets the mtime of the snapshot file"""
        return os.path.getmtime(self.__path)

    def add(self, path, hash):
        return self.__files.add(path, (hash, os.path.getmtime(path)))

    def get(self, path):
        return self.__files.get(path)

    def write(self):
        """Writes the current state of the snapshot back to the snapshot file"""
        with open(self.__path, 'wb') as file:
            json.dump(self.__data, file)#, indent=4, sort_keys=True)

class CachedCommunicator:
    """Wrapper around the Communicator classes provided by adapters, but maintains a local cache."""

    def __init__(self, root, cache_path, force, communicator):
        """
        Initialize the communicator.

        Args:
            root: the root of the repository
            cache_path: the path to the cache directory
            force: if true, always resolve files even if the snapshot shows them up-to-date
            communicator: the communicator to wrap
        """

        global snapshot, snapshot_lock

        if os.path.exists(cache_path) and not os.path.isdir(cache_path):
            raise RuntimeError('cache is not a directory, please remove it: ' + cache_path)

        # create if it doesn't exist
        try:
            os.mkdir(cache_path)
        except OSError:
            pass

        self.__cache = cache_path
        self.__force = force
        self.__comm = communicator
        
        with snapshot_lock:
            if snapshot is None:
                snapshot = Snapshot(root)

    def get(self, hash, dest):
        """
        Copies an object from the cache to a destination, downloading it if necessary.

        Args:
            hash: the name of the object (the hash of the file)
            dest: the path to which the object should be copied
        """
        global snapshot, snapshot_lock

        if not self.__force:
            try:
                with snapshot_lock:
                    snapdata = snapshot.get(dest)

                if (snapdata is not None and
                    # if the target hasn't been modified since the last snapshot
                    os.path.getmtime(dest) <= snapdata[1] and
                    # and the new hash is the same as the one in the snapshot
                    snapdata[0] == hash):
                    # then there's nothing to do
                    return
            except OSError:
                # if we have no snapshot or dest doesn't exist, we can't optimize
                pass

        cached = os.path.join(self.__cache, hash)

        if not os.path.exists(cached):
            self.__comm.get(hash, cached)

        if not os.path.exists(cached):
            raise RuntimeError("failed to download object: " + hash)

        if not os.path.isfile(cached):
            raise RuntimeError("stray non-file object in cache, please remove: " + cached)

        dir = os.path.dirname(dest)
        if dir:
            # create if it doesn't exist
            try:
                os.makedirs(os.path.dirname(dest))
            except OSError:
                pass
        shutil.copy(cached, dest)

        with snapshot_lock:
            snapshot.add(dest, hash)

    def put(self, source, hash):
        """
        Uploads an object to the remote, keeping a copy in the local cache.

        Args:
            source: the file to upload
            hash: the name of the object to create (the hash of the file)
        """
        global snapshot, snapshot_lock

        shutil.copy(source, os.path.join(self.__cache, hash))
        self.__comm.put(source, hash)

        with snapshot_lock:
            snapshot.add(source, hash)
