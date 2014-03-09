import sys
import traceback

# should be set by clients to the desired verbosity level
verbosity = 2

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
        tb = traceback.format_exc()
        if tb != "None\n":
            print tb
        else:
            print trace
    else:
        print "error: " + msg
    sys.exit(1)
