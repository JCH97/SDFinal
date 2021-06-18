from multiprocessing import Pool
import time
import hashlib

def get_hash(string):
    sha1 = hashlib.sha1()
    sha1.update(string)
    return int.from_bytes(sha1.digest(), byteorder='big') % (1 << ID_SPACE_SIZE)

print(get_hash('abel'))