import sys
import traceback

# should be set by clients to the desired verbosity level
verbosity = 2

# prevent buf
class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream

   def write(self, data):
       self.stream.write(data)
       self.stream.flush()

   def __getattr__(self, attr):
       return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)

def info(msg):
    if verbosity >= 3:
        print "info: " + msg

def warning(msg):
    if verbosity >= 2:
        print "warning: " + msg

def message(msg):
    if verbosity >= 1:
        print msg

def error(msg, trace=None):
    if verbosity >= 3:
        # generate a traceback if it came from this thread,
        # otherwise the traceback should have been passed
        if trace is not None:
            print trace
        else:
            print traceback.format_exc()
    else:
        print "error: " + msg
    sys.exit(1)
