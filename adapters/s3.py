import boto
import hashlib
import os
import os.path
import shutil
import tempfile
import threading

thread_local = threading.local()

class Communicator:
    def __init__(self, config):
        self.__id = config['id']
        self.__secret = config['secret']
        self.__bucket = config['bucket']

        # unique key under which we can cache our connection to the S3 bucket
        self.__key = hashlib.sha1(self.__id + self.__secret + self.__bucket).hexdigest()

    def get(self, hash, dest):
        key = self.__get_key(hash)
        tmpfd, tmp = tempfile.mkstemp()
        with os.fdopen(tmpfd, 'wb') as file:
            key.get_contents_to_file(file)
        shutil.move(tmp, dest)

    def put(self, source, hash):
        self.__get_key(hash).set_contents_from_filename(source)

    def __get_key(self, hash):
        # each thread uses its own connection, cached to thread-local storage
        key, bucket = getattr(thread_local, 'bucket', (None, None))
        if bucket is None or key != self.__key:
            conn = boto.connect_s3(self.__id, self.__secret)
            bucket = conn.get_bucket(self.__bucket)
            thread_local.bucket = (self.__key, bucket)

        key =  bucket.new_key(hash)

        return key
