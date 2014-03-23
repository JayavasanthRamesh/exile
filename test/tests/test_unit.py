import hashlib
import imp
import os
import random
import struct
import tempfile
import unittest

class TestHash(unittest.TestCase):
    def setUp(self):
        random.seed(563143)

        me = os.path.dirname(os.path.realpath(__file__))
        root = os.path.dirname(os.path.dirname(me))
        file, path, desc = imp.find_module('exile', [root])
        self.__hasher = imp.load_module('exile', file, path, desc).hash

    def trySize(self, size):
        tmpfd, tmp = tempfile.mkstemp()

        with os.fdopen(tmpfd, 'wb') as file:
            for _ in range(size):
                file.write(struct.pack('<Q', random.getrandbits(64)))

        with open(tmp, 'rb') as file:
            self.assertEqual(hashlib.sha1(file.read()).hexdigest(), self.__hasher(tmp))

        os.remove(tmp)

    def test_tiny(self):
        self.trySize(2)

    def test_small(self):
        self.trySize(1024)

    def test_medium(self):
        self.trySize(100000)

    def test_large(self):
        self.trySize(2000000)