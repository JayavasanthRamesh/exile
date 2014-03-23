import remote
import log
import files
import worker

import hashlib

def hash(path):
    """Compute the SHA1 hash of a file"""

    with open(path, 'rb') as file:
        h = hashlib.sha1()

        for block in iter(lambda: file.read(65536), ''):
            h.update(block)

        return h.hexdigest()