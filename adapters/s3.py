import boto
import os
import os.path
import shutil
import tempfile

template = {
    "id": "<Access Key ID>",
    "secret": "<Secret Access Key>",
    "bucket": "mybucket",
    "encrypt": False
}

class Communicator:
    def __init__(self, config):
        try:
            # grab the configuration values to catch missing config early
            self.__id = config['id']
            self.__secret = config['secret']
            self.__bucket_name = config['bucket']
            self.__bucket_conn = None   # connection initialized lazily
        except KeyError as e:
            raise Exception("missing required configuration: " + str(e))

        self.__encrypt = config.get('encrypt', False)

    def __bucket(self):
        """Lazily creates the S3 connection, which is then reused for future requests."""
        if self.__bucket_conn is None:
            # uses HTTPS by default
            conn = boto.connect_s3(self.__id, self.__secret)
            self.__bucket_conn = conn.get_bucket(self.__bucket_name)
        return self.__bucket_conn

    def get(self, hash, dest):
        key = self.__bucket().new_key(hash)
        tmpfd, tmp = tempfile.mkstemp()
        with os.fdopen(tmpfd, 'wb') as file:
            key.get_contents_to_file(file)
        shutil.move(tmp, dest)

    def put(self, source, hash):
        self.__bucket().new_key(hash).set_contents_from_filename(source, encrypt_key=self.__encrypt)
