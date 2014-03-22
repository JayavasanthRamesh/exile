Exile
=====

`exile` is a repository management tool designed to be used alongside Git. Its two core functions are to move files to and from a datastore, keeping track of these files in a local JSON manifest.

The primary use case for `exile` is to provide a way to track binary files in Git without actually checking them in. With `exile`, the only thing that gets checked in to the repository is a single JSON manifest. This file contains configuration information along with the a record of which files have been exiled and their revision.

Example
-------

```bash
$ echo a > a
$ exile.py init -t local
Initialized manifest with remote type 'local'
$ mkdir -p /tmp/exile-test
$ vim exile.manifest    # change "/path/to/repo" to "/tmp/exile-test"
$ exile.py add a
adding: a
$ rm a
$ exile.py resolve a
resolving: a
$ cat a
a
$ cat exile.manifest
{
    "files": {
        "a": "3f786850e387550fdab836ed7e6dc881de23001b"
    },
    "remote": {
        "location": "/tmp/exile-test",
        "type": "local"
    }
}
```

Adapters
--------

`exile` communicates with the datastore of your choice via adapters. These are just simple Python modules that provide access into the protocol of your choice. Adapters for [S3](http://aws.amazon.com/s3/) and local datastores are supported out of the box.

See [`adapters/`](adapters/README.md) for more information on writing new adapters.

Commands
--------

### init

This command is purely for convenience when creating a new repository. It simply creates a new manifest file and fills it with a template configuration provided by the adapter you are using.

### add

Add (or update) files and/or directories to exile. This involves pushing the files to the remote repository and updating the configuration file accordingly.

Multiple paths can be specified, and directories will be added recursively.

### resolve

Pull files from the remote repository into your local workspace. If the necessary files are not present in your local cache, they will be pulled from the remote. Syntax is similar to `add`.

### cache

`exile` maintains two types of caches: a local object cache and a workspace "snapshot". The  of all objects moving to and from the remote repository in order to prevent unnecessary network requests when switching between versions. The `cache` command provides some functionality for cleaning and inspecting these caches.

Backstory
---------

`exile` was designed after using [git-exile](https://github.com/patstam/git-exile) on a large project for a few months. It quickly became clear that it would be incredibly difficult to use Git's clean and smudge filters and maintain acceptable performance across platforms. Several problems, primarily the necessity of each filter execution spinning up a new process and the frequency at which Git calls these filters (even for `status`) meant that the solution simply wasn't performant with any sizable number of exiled files.

`exile` has been designed to be used *alongside* Git instead of depending on it directly and has performance as one of its main design goals.
