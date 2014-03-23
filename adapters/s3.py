import boto
import hashlib
import os
import os.path
import tempfile

template = {
    "id": "<Access Key ID>",
    "secret": "<Secret Access Key>",
    "bucket": "mybucket",
    "encrypt": False,
    "reduced_redundancy": False
}

def compute_hash(path):
    """Compute the SHA1 hash of a file"""

    with open(path, 'rb') as file:
        h = hashlib.sha1()

        for block in iter(lambda: file.read(65536), ''):
            h.update(block)

        return h.hexdigest()

class Communicator:
    def __init__(self, config, key_class=None):
        """
        Initialize the communicator

        Args:
            config: the configuration specified in the manifest file
            key_class: if specified, set as the key factory of the boto Bucket object
        """
        try:
            # grab the configuration values to catch missing config early
            self.__id = config['id']
            self.__secret = config['secret']
            self.__bucket_name = config['bucket']
            self.__bucket_conn = None   # connection initialized lazily
        except KeyError as e:
            raise Exception("missing required configuration: " + str(e))

        self.__key_class = key_class
        self.__encrypt = config.get('encrypt', False)
        self.__rr = config.get('reduced_redundancy', False)

    def __bucket(self):
        """Lazily creates the S3 connection, which is then reused for future requests."""
        if self.__bucket_conn is None:
            # uses HTTPS by default
            conn = boto.connect_s3(self.__id, self.__secret)
            self.__bucket_conn = conn.get_bucket(self.__bucket_name)
            if self.__key_class is not None:
                self.__bucket_conn.key_class = self.__key_class
        return self.__bucket_conn

    def get(self, hash, dest):
        key = self.__bucket().get_key(hash)
        if key is None:
            raise RuntimeError("no such key: " + hash) 

        # check for validity after download, retry once
        for tries in range(2):
            tmpfd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.realpath(dest)))
            with os.fdopen(tmpfd, 'wb') as file:
                key.get_contents_to_file(file)

            if hash == compute_hash(tmp):
                try:
                    os.rename(tmp, dest)
                except WindowsError as e:
                    # if dest already exists then another thread beat us to it
                    if e.winerror == 183:
                        os.remove(tmp)
                    else:
                        raise e
                return
            else:
                os.remove(tmp)

        raise Exception('error: object corrupt: ' + hash)

    def put(self, source, hash):
        self.__bucket().new_key(hash).set_contents_from_filename(source, encrypt_key=self.__encrypt, reduced_redundancy=self.__rr)
