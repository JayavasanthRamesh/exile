import sys

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

def error(msg):
    print "error: " + msg
    sys.exit(1)