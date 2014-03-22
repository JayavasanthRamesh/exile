from core import *

import copy
import hashlib

class AddTest(ExileTest):
    def assertAdded(self, contents):
        hash = hashlib.sha1(contents).hexdigest()
        self.assertInCache(hash)
        self.assertInRepo(hash)

class BasicAddTest(AddTest):
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

class PurgeTest(AddTest):
    def setUp(self):
        self._files = {
            os.path.join('dir', 'a'): 'a',
            os.path.join('dir', 'b'): 'b',
            os.path.join('dir', 'c', 'd'): 'd',
            os.path.join('dir', 'c', 'e'): 'e'
        }
        super(PurgeTest, self).setUp()

        self.exile_add('dir')
        for _, contents in self._files.iteritems():
            self.assertAdded(contents)

    def assertUpdated(self, files):
        self.clearWorkspace()
        self.exile_resolve('dir')
        self.assertState(files)

    def test_replace(self):
        # clear repo so we can see what got uploaded
        self.clearRepo()

        self.exile_add('-p', 'dir')

        # we only removed files, so nothing should have been pushed to the repo
        self.assertTrue(len(os.listdir(self._repo)) == 0)

    def test_purge(self):
        expected = copy.deepcopy(self._files)

        # indicies to remove
        to_remove = [1, 3]
        # mappings to add
        to_add = [
            (os.path.join('dir', 'x'), 'x'),
            (os.path.join('dir', 'c', 'y'), 'y'),
        ]

        removed = []
        for i in to_remove:
            path = self._files.keys()[i]
            os.remove(path)
            del expected[path]
            removed.append(path)

        for path, contents in to_add:
            expected[path] = contents
            create_file(self._dir, path, contents)

        self.exile_add('-p', 'dir')

        self.assertUpdated(expected)
        for path in removed:
            self.assertTrue(not os.path.exists(path))