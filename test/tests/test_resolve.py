from core import *

import hashlib
import os
import shutil

class ResolveTest(ExileTest):
    def setUp(self):
        super(ResolveTest, self).setUp()

        # add all files
        self.exile_add(*self._files.keys())

        self.clearWorkspace()

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

    def test_resolve(self):
        os.mkdir('dir')
        os.chdir('dir')
        self.exile_resolve('a', 'b')
        for path, contents in self._files.iteritems():
            self.assertResolved(path, contents)