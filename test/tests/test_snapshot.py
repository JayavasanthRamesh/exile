from core import *

import hashlib
import json
import os
import time

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

        self.exile_add(*self._files.keys())

    def test_add_all(self):
        self.assertSnapshot(self._files)

    def test_resolve(self):
        os.remove(SNAPSHOT_PATH)

        path, contents = self._files.items()[0]
        self.exile_resolve(path)
        self.assertSnapshot( { path: contents } )

    def test_no_change(self):
        os.remove(SNAPSHOT_PATH)
        path, contents = self._files.items()[0]

        # resolve to generate a snapshot
        self.exile_resolve(path)
        self.assertResolved(path, contents)
        before = os.path.getmtime(path)

        # resolve again, should not touch file
        self.exile_resolve(path)
        self.assertResolved(path, contents)
        self.assertEqual(before, os.path.getmtime(path))

    def test_changed(self):
        os.remove(SNAPSHOT_PATH)
        path, contents = self._files.items()[0]

        # resolve to generate a snapshot
        self.exile_resolve(path)
        self.assertResolved(path, contents)
        before = os.path.getmtime(path)

        # let time pass so that our modification is clearly after the snapshot time
        time.sleep(1)

        # overwrite file with new contents
        newcontents = 'newcontents'
        with open(path, 'w') as file:
            file.write(newcontents)
        self.assertContents(path, newcontents)

        # resolve again, should overwrite the file
        self.exile_resolve(path)
        self.assertResolved(path, contents)
        self.assertLess(before, os.path.getmtime(path))