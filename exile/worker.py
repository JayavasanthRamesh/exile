import imp
import log
import multiprocessing
import os
import Queue
import remote
import threading

def create_communicator(config):
    """Factory for communicator objects based on the configured type."""

    type = config['type']

    # finds the module (python file) with the same name as the specified type in the "adapters" directory and loads it
    me = os.path.dirname(os.path.realpath(__file__))
    parent = os.path.dirname(me)
    file, path, desc = imp.find_module(type, [os.path.join(parent, 'adapters')])
    comm_module = imp.load_module(type, file, path, desc)

    return comm_module.Communicator(config)

def worker_main(queue, comm):
	while True:
		work = queue.get()
		log.info("worker processing item")
		work["func"](comm, *work["args"])
		queue.task_done()

class AsyncCommunicator:
    """Wrapper around the Communicator classes provided by adapters that distributes work across multiple threads."""

    def __init__(self, cache_path, config):
    	self.__queue = Queue.Queue()
    	comm = remote.CachedCommunicator(cache_path, create_communicator(config))

    	threads = min(4, multiprocessing.cpu_count())
    	log.info("spawning %d worker threads" % (threads))
    	for x in range(threads):
    		t = threading.Thread(target=worker_main, args=(self.__queue, comm))
    		t.daemon = True
    		t.start()

    def get(self, hash, dest):
    	self.__queue.put( { "func": remote.CachedCommunicator.get, "args": (hash, dest) } )

    def put(self, source, hash):
    	self.__queue.put( { "func": remote.CachedCommunicator.put, "args": (source, hash) } )

    def join(self):
    	log.info("waiting for work to complete")
    	self.__queue.join()
