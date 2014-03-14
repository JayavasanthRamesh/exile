from core import *

import hashlib
import os
import shutil

class ResolveTest(ExileTest):
    def setUp(self):
        super(ResolveTest, self).setUp()

        # add all files
        self.exile_add(*self._files.keys())

        # save the contents of the config file
        with open(os.path.join(self._dir, 'exile.manifest'), 'r') as file:
            config = file.read()

        # clear out the repo directory
        shutil.rmtree(self._repo)
        os.mkdir(self._repo)

        # replace the config file
        with open(os.path.join(self._dir, 'exile.manifest'), 'w') as file:
            file.write(config)

    def assertResolved(self, path, contents):
        fullpath = os.path.join(self._dir, path)
        self.assertFile(fullpath, path)
        with open(fullpath, 'r') as file:
            self.assertEqual(file.read(), contents)
        self.assertInCache(hashlib.sha1(contents).hexdigest())

class BasicResolveTest(ResolveTest):
    def test_all(self):
        self.exile_resolve(*self._files.keys())
        for path, contents in self._files.iteritems():
            self.assertResolved(path, contents)

    def test_one(self):
        path, contents = self._files.items()[0]
        self.exile_resolve(path)
        self.assertResolved(path, contents)

class SubDirResolveTest(ResolveTest):
    def setUp(self):
        self._files = {
            os.path.join('dir', 'a'): 'a',
            os.path.join('dir', 'b'): 'b'
        }
        super(SubDirResolveTest, self).setUp()
        
        for path, _ in self._files.iteritems():
            os.remove(path)

    def test_resolve(self):
        os.chdir('dir')
        self.exile_resolve('a', 'b')
        for path, contents in self._files.iteritems():
            self.assertResolved(path, contents)