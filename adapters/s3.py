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
            # uses HTTPS by default
            conn = boto.connect_s3(config['id'], config['secret'])
            self.__bucket = conn.get_bucket(config['bucket'])
        except KeyError as e:
            raise Exception("missing required configuration: " + str(e))

        self.__encrypt = config.get('encrypt', False)

    def get(self, hash, dest):
        key = self.__bucket.new_key(hash)
        tmpfd, tmp = tempfile.mkstemp()
        with os.fdopen(tmpfd, 'wb') as file:
            key.get_contents_to_file(file)
        shutil.move(tmp, dest)

    def put(self, source, hash):
        self.__bucket.new_key(hash).set_contents_from_filename(source, encrypt_key=self.__encrypt)
