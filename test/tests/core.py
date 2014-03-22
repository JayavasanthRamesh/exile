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
    TEST_DIR = os.path.abspath('/tmp/exile-test')    # location of the exile directory
    REPO_DIR = os.path.abspath('/tmp/exile-repo')    # location of the "remote" repository
else:
    TEST_DIR = ''
    REPO_DIR = ''

EXILE = os.path.realpath('../exile.py')

def create_file(dir, path, contents):
    """Creates a file containing contents a the path created by concatenating dir and path"""

    fullpath = os.path.join(dir, path)
    fulldir = os.path.dirname(fullpath)

    if fulldir:
        try:
            os.makedirs(fulldir)
        except OSError:
            pass

    with open(fullpath, 'w') as file:
        file.write(contents)

def get_directory(default):
    """
    Returns a clean, empty directory.

    If default is a path, the directory is place there. Otherwise, a temporary directory is created
    """
    if default:
        # remove existing if present
        try:
            shutil.rmtree(default)
        except OSError:
            pass

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
        os.path.join('c', 'd'): 'D',
        os.path.join('c', 'e', 'f'): 'F',
        'a=b:c': 'complex'
    }

    # the default configuration
    # remote.location set at setUp time
    _config = {
        'remote': {
            'type': 'local',
            'cache': '.exile.cache'
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

    def assertContents(self, path, contents):
        fullpath = os.path.join(self._dir, path)
        self.assertFile(fullpath, path)
        with open(fullpath, 'r') as file:
            self.assertEqual(file.read(), contents)

    def assertResolved(self, path, contents):
        self.assertContents(path, contents)
        self.assertInCache(hashlib.sha1(contents).hexdigest())

    def exile_add(self, *args):
        self.__exile('add', *args)

    def exile_resolve(self, *args):
        self.__exile('resolve', *args)

    def clearRepo(self):
        for file in os.listdir(self._repo):
            os.remove(os.path.join(self._repo, file))

    def clearWorkspace(self):
        for file in os.listdir(self._dir):
            if file == 'exile.manifest':
                continue

            full = os.path.join(self._dir, file)
            if os.path.isfile(full):
                os.remove(full)
            elif os.path.isdir(full):
                shutil.rmtree(full)

    def __exile(self, *args):
        subprocess.call(['python', EXILE, '-v0'] + list(args))

    def tearDown(self):
        # make sure we aren't inside the folders we're about to delete
        os.chdir('/')
        if not TEST_DIR:
            shutil.rmtree(self._dir)
        if not REPO_DIR:
            shutil.rmtree(self._repo)