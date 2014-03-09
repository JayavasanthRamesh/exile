import imp
import log
import multiprocessing
import os
import Queue
import remote
import threading
import traceback

def create_communicator(config):
    """Factory for communicator objects based on the configured type."""

    type = config['type']

    # finds the module (python file) with the same name as the specified type in the "adapters" directory and loads it
    me = os.path.dirname(os.path.realpath(__file__))
    parent = os.path.dirname(me)
    file, path, desc = imp.find_module(type, [os.path.join(parent, 'adapters')])
    comm_module = imp.load_module(type, file, path, desc)

    return comm_module.Communicator(config)

def worker_main(queue, comm, manager):
    while manager.last_exception is None:
        work = queue.get()
        try:
            log.info("worker processing item")
            work["func"](comm, *work["args"])
        except Exception as e:
            manager.last_exception = (str(e), traceback.format_exc())
        finally:
            queue.task_done()

class AsyncCommunicator:
    """Wrapper around the Communicator classes provided by adapters that distributes work across multiple threads."""

    def __init__(self, cache_path, config):
        self.last_exception = None
        self.__queue = Queue.Queue()

        for x in range(4):
            comm = remote.CachedCommunicator(cache_path, create_communicator(config))
            t = threading.Thread(target=worker_main, args=(self.__queue, comm, self))
            t.daemon = True
            t.start()

    def __checked(f):
        def result(self, *args):
            if self.last_exception is not None:
                log.error(*self.last_exception)

            f(self, *args)

            if self.last_exception is not None:
                log.error(*self.last_exception)
        return result

    @__checked
    def get(self, hash, dest):
        self.__queue.put( { "func": remote.CachedCommunicator.get, "args": (hash, dest) } )

    @__checked
    def put(self, source, hash):
        self.__queue.put( { "func": remote.CachedCommunicator.put, "args": (source, hash) } )

    @__checked
    def join(self):
        log.info("waiting for work to complete")
        self.__queue.join()
