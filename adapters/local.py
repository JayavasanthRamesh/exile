import shutil
import os
import os.path

class Communicator:
    def __init__(self, config):
        self.__location = config['location']

        if not os.path.exists(self.__location):
            raise RuntimeError("configured repository location does not exist: " + self.__location)

        if not os.path.isdir(self.__location):
            raise RuntimeError("configured repository location is not a directory: " + self.__location)

    def get(self, hash, dest):
        shutil.copy(self.__repoPath(hash), dest)

    def put(self, source, hash):
        shutil.copy(source, self.__repoPath(hash))

    def __repoPath(self, hash):
        return os.sep.join([self.__location, hash])
