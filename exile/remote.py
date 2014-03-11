import os
import shutil

class CachedCommunicator:
    """Wrapper around the Communicator classes provided by adapters, but maintains a local cache."""

    def __init__(self, cache_path, communicator):
        if os.path.exists(cache_path) and not os.path.isdir(cache_path):
            raise RuntimeError('cache is not a directory, please remove it: ' + cache_path)

        # create if it doesn't exist
        try:
            os.mkdir(cache_path)
        except OSError:
            pass

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