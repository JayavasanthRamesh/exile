Adapters
========

Each module in this folder provides an adapter used to send and recieve files
between a remote repository and the local machine. This allows you to easily
extend exile to support various file transfer methods and protocols by just
dropping in a new adapter.

Interface
---------

Each adapter must contain a class named `Communicator` with `get` and `put`
methods, according the the following template:

    class Communicator:
        def __init__(self, config):
            """
            Initialize using the supplied configuation.

            Args:
                config: the parsed JSON configuration for the "remote" section of the manifest
            """
            pass

        def get(self, hash, dest):
            """
            Download an object to a local destination.

            Args:
                hash: the name of the object to download
                dest: the local path at which the downloaded object should be saved
            """
            pass

        def put(self, source, hash):
            """
            Upload a local file as an object on the remote.

            Args:
                source: the local path at which file resides
                hash: the name of the object (the hash of the local file)
            """
            pass

It is also recommended that each adapter module contain a variable named
'template' that contains all the configuration values used by the adapter.
This is used by the `init` command to populate a manifest template.

For example, the template for the S3 adapter is as follows:

```python
template = {
    "id": "<Access Key ID>",
    "secret": "<Secret Access Key>",
    "bucket": "mybucket",
    "encrypt": False
}
```

Configuration
-------------

Once you have your Communicator written, you just need to add the appropriate
configuration to your manifest in the "remote" section. Take the following
simple manifest:

    {
        "remote": {
            "type": "local",
            "location": "/tmp/exile-test"
        },
        "files": {}
    }

Here we only care about the "remote" section. The only keys that exile knows
about are "type", which tells us which module to use for communication, and
"cache" which specifies the directory in which the local object cache should
live. The rest of the dictionary can be arbitrary key-value pairs that are then
made available to the communicator in its constructor.

In this case, the "local" communicator only needs a path to the repository
location, so we only have one other key. When we create the communicator, 
we pass the "remote" dict to the constructor, so it will recieve:

    {
        "type": "local",
        "location": "/tmp/exile-test"
    }

Keep in mind that these additional type-specific keys can be arbitrary
values, and so can be as complex as necessary (possibly containing things
like nested dicts, etc).
