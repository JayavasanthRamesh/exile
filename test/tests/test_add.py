from core import *

import hashlib

class AddTest(ExileTest):
    def assertAdded(self, contents):
        hash = hashlib.sha1(contents).hexdigest()
        self.assertInCache(hash)
        self.assertInRepo(hash)

    def test_setup(self):
        self.assertState(self._files)

    def test_all(self):
        self.exile_add(*self._files.keys())
        for _, contents in self._files.iteritems():
            self.assertAdded(contents)

    def test_one(self):
        path, contents = self._files.items()[0]
        self.exile_add(path)
        self.assertAdded(contents)

    def test_update(self):
        path = 'updateme'
        initial = 'initial'
        updated = 'different'

        # create the file and add it
        create_file(self._dir, path, initial)
        self.exile_add(path)
        self.assertAdded(initial)

        # change the contents and add it again (update)
        create_file(self._dir, path, updated)
        self.exile_add(path)
        self.assertAdded(updated)
