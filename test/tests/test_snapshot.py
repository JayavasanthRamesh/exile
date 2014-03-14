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
            # make sure the snapshot has the right hash
            value = snapshot
            for component in path.split('/'):
                value = value[component]
            self.assertEqual(value, hashlib.sha1(contents).hexdigest())

            # make sure the snapshot's mtime is not less than the file's
            file_mtime = os.path.getmtime(path)
            snapshot_mtime = os.path.getmtime(SNAPSHOT_PATH)
            self.assertLessEqual(file_mtime, snapshot_mtime)

    def setUp(self):
        self._files = {
            'a': 'a',
            'dir/b': 'b'
        }
        super(SnapshotTest, self).setUp()


    def test_add_all(self):
        self.exile('add *')
        self.assertSnapshot(self._files)

    def test_resolve(self):
        self.exile('add *')

        os.remove(SNAPSHOT_PATH)

        path, contents = self._files.items()[0]
        self.exile('resolve ' + path)
        self.assertSnapshot( { path: contents } )
