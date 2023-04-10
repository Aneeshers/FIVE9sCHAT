HEADER_LENGTH = 10

# Message objects are created from buffer in protocol_unpack
# and initialized in protocol_action and handel client in socket_server/server.py
# Data Stored:
#  - sender -> message sender username
#  - recipient -> message recipient username
#  - data -> the message to be sent to the recipient
class Message:
    # Initalize Message() object
    def __init__(self, recipient, sender, message):
        self.sender = sender
        self.recipient = recipient
        self.data = message 

    # Returns the message encoded with header(also encoded)
    def encode(self):
        encoded_message = f"M:{self.recipient}:{self.sender}:{self.data}".encode('utf-8')
        header = f"{len(encoded_message) :< {HEADER_LENGTH}}".encode('utf-8')

        return header+encoded_message
    def encodeJustMessage(self):
        encoded_message = f"M:{self.recipient}:{self.sender}:{self.data}".encode('utf-8')
        return encoded_message
    
    def print(self):
        print("sender: ", self.sender)
        print("recipient: ", self.recipient)
        print("message: ", self.data)
    
    # Creates a Message() object from buffer
    @staticmethod
    def createMessageFromBuffer(header):
        #break down raw packet and construct message
        header = header.split(":",3)
        sender = header[1]
        recipient = header[2]
        data = header[3]
        return Message(sender, recipient, data)
    
    @staticmethod 
    def equals(Message1, Message2):
        m1sender = Message1.sender
        m1recipient = Message1.recipient
        m1data = Message1.data

        m2sender = Message2.sender
        m2recipient = Message2.recipient
        m2data = Message2.data

        if m1sender != m2sender:
            return False
        if m1recipient != m2recipient:
            return False
        if m1data != m1data:
            return False
        return True

