from core import *

import hashlib
import json
import os

# relative to repo root
SNAPSHOT_PATH = '.exile.snapshot'

class SnapshotTest(ExileTest):
    def assertSnapshot(self, files):
        with open(SNAPSHOT_PATH, 'r') as file:
            snapshot = json.load(file)

        for path, contents in files.iteritems():
            # split the path into components
            components = []
            head, tail = os.path.split(path)
            while tail:
                components = [tail] + components
                head, tail = os.path.split(head)

            # make sure the snapshot has the right hash
            value = snapshot
            for component in components:
                value = value[component]
            self.assertEqual(value, hashlib.sha1(contents).hexdigest())

            # make sure the snapshot's mtime is not less than the file's
            file_mtime = os.path.getmtime(path)
            snapshot_mtime = os.path.getmtime(SNAPSHOT_PATH)
            self.assertLessEqual(file_mtime, snapshot_mtime)

    def setUp(self):
        self._files = {
            'a': 'a',
            os.path.join('dir', 'b'): 'b'
        }
        super(SnapshotTest, self).setUp()


    def test_add_all(self):
        self.exile_add(*self._files.keys())
        self.assertSnapshot(self._files)

    def test_resolve(self):
        self.exile_add(*self._files.keys())

        os.remove(SNAPSHOT_PATH)

        path, contents = self._files.items()[0]
        self.exile_resolve(path)
        self.assertSnapshot( { path: contents } )
