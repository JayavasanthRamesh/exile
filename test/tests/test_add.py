from core import *

class AddTest(ExileTest):
    def assertAdded(self, contents):
        hash = hashlib.sha1(contents).hexdigest()
        self.assertInCache(hash)
        self.assertInRepo(hash)

    def test_setup(self):
        self.assertState(self._files)

    def test_all(self):
        self.exile('add *')
        for path, contents in self._files.iteritems():
            self.assertAdded(contents)

    def test_one(self):
        path, contents = self._files.items()[0]
        self.exile('add ' + path)
        self.assertAdded(contents)
