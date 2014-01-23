#!/usr/bin/env python

import unittest
import tempfile
import shutil
import os
import json

def create_file(dir, path, contents):
    fullpath = os.path.join(dir, path)
    fulldir = os.path.dirname(fullpath)
    if fulldir and not os.path.exists(fulldir):
        os.makedirs(fulldir)

    with open(fullpath, 'w') as file:
        file.write(contents)

class ExileTest(unittest.TestCase):
    # mapping from relative path to file contents
    # the test repository will be initialized to this state
    # subclasses can redefine this value
    _files = {
        'a': 'A',
        'b': 'B',
        'c/d': 'D',
        'c/e/f': 'F',
        'a=b:c': 'complex'
    }

    # the default configuration
    # remote.location set at setUp time
    _config = {
       "remote": {
            "type": "local",
        } 
    }

    def setUp(self):
        # create temp directory
        self.__dir = tempfile.mkdtemp()S

        # create config file
        with open(os.path.join(self.__dir, 'exile.manifest'), 'w') as file:
            json.dump(_config, file, indent=4, sort_keys=True)

        # initialize files
        for path, contents in _files.iteritems():
            create_file(self.__dir, path, contents)

    def assertState(files):
        for path, expected in files.iteritems():
            self.assertTrue(os.path.exists(path), "file does not exist: " + path)
            self.assertTrue(os.path.isfile(path), "not a file: " + path)
            with open(path, 'r') as file:
               actual = file.read() 
            self.assertEqual(actual, expected, "unexpected contents: " + path)

    def tearDown(self):
        shutil.rmtree(self.__dir)

class BasicFunctionalTest(ExileTest):
    def test_setup(self):
        assertState(files)

if __name__ == '__main__':
    unittest.main()
