HEADER_LENGTH = 10


# Command objects are created from buffer in protocol_unpack
# Data Stored:
#  - socket information
#  - username -> user who created it object
#  - actionType -> either List Account(LA) or Delete Account(DA)
#  - data -> data needed for later use in operations
class Command:
    def __init__(self, socket, data, username,type_):
        self.socket = socket
        self.username = username
        self.actionType = type_
        self.data = data

    @staticmethod
    def createCommandFromBuffer(client, data, username, type_):
        return Command(client, data ,username,type_)