import os
import binascii
HEADER_LENGTH = 10

def sendPickleFile(file_,client):
    pickle_file = binascii.hexlify(file_)
    header = f"{len(pickle_file) :< {HEADER_LENGTH}}".encode('utf-8')
    client.sendall(header)

