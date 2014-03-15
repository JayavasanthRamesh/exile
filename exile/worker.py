import imp
import log
import multiprocessing
import os
import Queue
import remote
import threading
import traceback

def load_comm_module(config):
    """Loads the appropriate adapter module based on the configured type."""

    type = config['type']

    # finds the module (python file) with the same name as the specified type in the "adapters" directory and loads it
    me = os.path.dirname(os.path.realpath(__file__))
    parent = os.path.dirname(me)
    file, path, desc = imp.find_module(type, [os.path.join(parent, 'adapters')])
    return imp.load_module(type, file, path, desc)

THREAD_COUNT = 6    # based on the number of concurrent connections from Chrome

class AsyncCommunicator:
    """Wrapper around the Communicator classes provided by adapters that distributes work across multiple threads."""

    def __init__(self, root, cache_path, config, force):
        # tracks exceptions thrown from worker threads
        self.__last_exception = None

        # work queue for worker threads
        self.__queue = Queue.Queue(1)   # maxsize 1 prevents callers from getting to far ahead

        # load the module here since importing isn't thread-safe
        comm_module = load_comm_module(config)

        # start all worker threads
        for x in range(THREAD_COUNT):
            t = threading.Thread(target=AsyncCommunicator.__worker_main, args=(self, root, cache_path, comm_module, config, force))
            t.daemon = True
            t.start()

    def __worker_main(self, root, cache_path, comm_module, config, force):
        """
        The entry point for worker threads. Pulls work from the queue as it
        becomes available.

        Args:
            root: the directory containing the config file
            cache_path: the path to the local cache directory
            comm_module: the Python module for the configured adapter
            config: the configuration necessary to construct a communicator
            force: if true, configure the communcator to force updates
        """

        comm = remote.CachedCommunicator(root, cache_path, force, comm_module.Communicator(config))

        # once any thread throws an exception, stop processing work
        while self.__last_exception is None:
            work = self.__queue.get()   # wait on the next task
            try:
                work["func"](comm, *work["args"])
            except Exception as e:
                self.__last_exception = (str(e), traceback.format_exc())
            finally:
                self.__queue.task_done()

    def __check_error(self):
        if self.__last_exception is not None:
            log.error(*self.__last_exception)

    def __add_task(self, task):
        full = True
        while full:
            try:
                self.__check_error()
                self.__queue.put(item=task, timeout=0.5)
                full = False
            except Queue.Full as e:
                pass

        self.__check_error()

    def get(self, hash, dest):
        self.__add_task( { "func": remote.CachedCommunicator.get, "args": (hash, dest) } )

    def put(self, source, hash):
        self.__add_task( { "func": remote.CachedCommunicator.put, "args": (source, hash) } )

    def join(self):
        """
        Blocks until all asynchronous get and put operations have finished.
        """

        self.__check_error()
        log.info("waiting for work to complete")
        self.__queue.join()
        self.__check_error()

        with remote.snapshot_lock:
            if remote.snapshot is not None:
                remote.snapshot.write()
