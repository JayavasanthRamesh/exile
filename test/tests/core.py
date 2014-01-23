import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

# If set, tests will create their repository in these directories.
# This is useful for debugging failing tests, but makes the
# tests less self-contained. Generally this should be left
# unset, so the tests will use generated temp directories
# instead
if False:
    TEST_DIR = '/tmp/exile-test'    # location of the exile directory
    REPO_DIR = '/tmp/exile-repo'    # location of the "remote" repository
else:
    TEST_DIR = ''
    REPO_DIR = ''

EXILE = os.path.realpath('../exile.py')

def create_file(dir, path, contents):
    """Creates a file containing contents a the path created by concatenating dir and path"""

    fullpath = os.path.join(dir, path)
    fulldir = os.path.dirname(fullpath)
    if fulldir and not os.path.exists(fulldir):
        os.makedirs(fulldir)

    with open(fullpath, 'w') as file:
        file.write(contents)

def get_directory(default):
    """
    Returns a clean, empty directory.

    If default is a path, the directory is place there. Otherwise, a temporary directory is created
    """
    if default:
        if os.path.exists(default):
            shutil.rmtree(default)

        os.makedirs(default)
        return default
    else:
        return tempfile.mkdtemp()

def hash(path):
    """Compute the SHA1 hash of a file"""

    with open(path, 'r') as file:
        return hashlib.sha1(file.read()).hexdigest()

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
        'remote': {
            'type': 'local',
        } 
    }

    def setUp(self):
        # create test directory
        self._dir = get_directory(TEST_DIR)
        self._repo = get_directory(REPO_DIR)
        self._config['remote']['location'] = self._repo

        # create config file
        with open(os.path.join(self._dir, 'exile.manifest'), 'w') as file:
            json.dump(self._config, file, indent=4, sort_keys=True)

        # initialize files
        for path, contents in self._files.iteritems():
            create_file(self._dir, path, contents)

        os.chdir(self._dir)

    def assertFile(self, fullpath, relative):
        self.assertTrue(os.path.exists(fullpath), "file does not exist: " + relative)
        self.assertTrue(os.path.isfile(fullpath), "not a file: " + relative)

    def assertState(self, files):
        """Assert that the exile directory matches the state described in the file mapping (see _files for an example)"""

        for path, expected in files.iteritems():
            fullpath = os.path.join(self._dir, path)
            self.assertFile(fullpath, path)
            with open(fullpath, 'r') as file:
               actual = file.read() 
            self.assertEqual(actual, expected)

    def assertObject(self, fullpath, relative):
        self.assertFile(fullpath, relative)
        self.assertEqual(hash(fullpath), os.path.basename(fullpath))

    def assertInCache(self, object):
        path = os.path.join('.exile.cache', object)
        fullpath = os.path.join(self._dir, path)
        self.assertObject(fullpath, path)

    def assertInRepo(self, object):
        self.assertObject(os.path.join(self._repo, object), object)

    def exile(self, args):
        subprocess.call('python ' + EXILE + ' -v0 ' + args, shell=True)

    def tearDown(self):
        if not TEST_DIR:
            shutil.rmtree(self._dir)
        if not REPO_DIR:
            shutil.rmtree(self._repo)