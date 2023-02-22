HEADER_LENGTH = 10

class Command:
    def __init__(self, socket, data, username,type_):
        self.socket = socket
        self.username = username
        self.actionType = type_
        self.data = data

    def sendConfirmation(self,socket,message):

        message = f"M:{self.username}:SERVER:{message}".encode('utf-8')
        socket.send(message)

    def deliverQueuedMessages(self):
        if self.queuedMessages == []:
            return self.sendConfirmation(self.socket,"No waiting messages!")
        for message in queuedMessages:
            message.send()
            queuedMessages = []

    # TODO this function needs to move outside of the account object
    def login(self, exists,client):
        if not exists:
            return self.sendConfirmation(client,"User does not exist!")
        online = True
        return self.sendConfirmation(client,"User Logged in Successfully")

    def logout(self):
        online = False
        self.socket.close()
        

    def delete(self,exists, clientDict):
        if not exists:
            self.sendConfirmation(self.socket,"User unable to be deleted!")
        else:
            self.sendConfirmation(self.socket,"Account successfully deleted!")
            self.socket.close()        



    def queueMessage(self,message_obj):
        self.queuedMessages.append(message_obj)


    @staticmethod
    def createCommandFromBuffer(client, external_data, data, type_):
        return Command(client, external_data ,data,type_)