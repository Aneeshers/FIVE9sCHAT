import threading
import socket

from message import Message
from command import Command

# Constants
HEADER_LENGTH = 10
HOST = '10.250.92.212'
PORT = 12340

# Connect sockets to server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

# Information storage structures

# Stores active socket
clients = []

# Stores active usernames
usernames = [] 


# Stores all active users {username:socket} pairs
clientID = {}

# Stores if a user is online or not all accounts {username:Boolean}
loginStatus = {}

# The server is always online so users cannot log into the server account
loginStatus['SERVER'] = True

# Stores all messages to offline users {username: Message()}
queuedMessages = {}

# Protocol action handles all actions by the server according to our Protocol
# Input is either a Message() or Command() object
def protocol_action(obj):

    # If the object is a Message() then we try to send the message
    if isinstance(obj, Message):

        # If recipient exists -> sends error to client if they do not
        if obj.recipient not in loginStatus:
            doesNotExist = "The user you are trying to contact does not exist."
            doesNotExist = Message(obj.sender, "SERVER", doesNotExist)
            sendToClient(obj.sender, doesNotExist.encode())

        # If recipient is logged-out -> Alerts sender and and queues the message
        elif not loginStatus[obj.recipient]:
            notlogin = obj.recipient + " is not logged in. But your message will be delivered"
            notlogin = Message(obj.sender, "SERVER", notlogin)
            sendToClient(obj.sender,notlogin.encode())
            if obj.recipient not in queuedMessages.keys():
                queuedMessages[obj.recipient] = []
            queuedMessages[obj.recipient].append(obj)

        # Else sends the message to recipient and delivery confirmation to sender
        elif (clientID[obj.recipient] in clients):
            success = "Your message has successfully delivered."
            success = Message(obj.sender, "SERVER", success)
            sendToClient(obj.recipient, obj.encode())
            sendToClient(obj.sender, success.encode())
    
    # If the object is a Command() then we execute the command
    if isinstance(obj, Command):

        # If Command type is DA -> Delete Account
        if obj.actionType == "DA":
                
            # User must be online execute this Command so no checks are needed

            # Send confirmation to user
            success = "Account-Successfully-Deleted"
            success = Message(obj.username, "SERVER", success)
            sendToClient(obj.username, success.encode())


            # Remove user from loginStatus and clientID list
            del loginStatus[obj.username]
            del clientID[obj.username]

            # Only delete from queued messages if user had queued messages. 
            if obj.username in queuedMessages.keys():
                del queuedMessages[obj.username]

        # If Command type is LA -> Lists all stored accounts with their login status
        elif obj.actionType == "LA":

            ## Generate account list
            allAccounts = 'LA|'

            # Append (active) or (inactive) to every username
            for account in obj.data:

                #  If username is active
                if obj.data[account]:
                    status = 'active'

                # If username is not active
                else:
                    status = 'inactive'
                
                # Add account status to list with "|", as a divider
                allAccounts += account + " ( " + status + " )" + "|"

            # Remove the last "|" if accounts exists 
            if len(allAccounts) > len("LA|"):
                allAccounts = allAccounts[:-1]

            # Sends list to client to display
            allAccounts = Message(obj.username, "SERVER", allAccounts)
            sendToClient(obj.username, allAccounts.encode())


# Protocol unpack creates Message() and Command() from protocol buffers
# Takes a client socket and encoded buffer data
def protocol_unpack(data,client):

    # Buffer data and splits on the colon 
    data = data.decode('UTF-8')
    dataSplit = data.split(":",3)

    # Retrieves type of message/command from buffer data
    type_ = dataSplit[0]

    if type_ == "M":
        return Message.createMessageFromBuffer(data)
    elif type_ == "LA":
        username = dataSplit[1]

        #TODO Implement createCommandFromBuffer
        # usage -> Command.createCommandFromBuffer(client, external_data, data)
        return Command.createCommandFromBuffer(client, loginStatus ,username,type_)
    elif type_ == "DA":
        #TODO Implement createCommandFromBuffer
        username = dataSplit[1]
        return Command.createCommandFromBuffer(client, None ,username,type_)

                
def broadcast(message):
    for client in clients:
        index = clients.index(client)
        username = usernames[index]

        message = Message(username, "SERVER", message)
        
        client.send(message.encode())

# Function to handle clients'connections
def sendToClient(username, message):

    client = clientID[username]
    client.send(message)



def handle_client(client):
    # First message will be list accounts
    data = client.recv(HEADER_LENGTH).decode('utf-8')
    data_length = int(data.strip())
    data = client.recv(data_length)

    ## Generate account list

    # obj.data {username: loginstatus}
    allAccounts = 'LA|'
    for account in loginStatus:
        #  username is active
        if loginStatus[account]:
            status = 'active'
        # username is not active
        else:
            status = 'inactive'
        allAccounts += account + " ( " + status + " )" + "|"
    if len(allAccounts) > len("LA|"):
        allAccounts = allAccounts[:-1]
    
    message = f"M:_:SERVER:{allAccounts}".encode('utf-8')
    header = f"{len(message) :< {HEADER_LENGTH}}".encode('utf-8')
    client.send(header+message)


    client_auth = False
    # Validation - conditions -> while not auth
    while not client_auth:
         
        data = client.recv(HEADER_LENGTH).decode('utf-8')
        # print("DATA 1:", data)
        data_length = int(data.strip())
        # print("DATA Length is ", data_length)
        data = client.recv(data_length).decode('utf-8')
        print("data is ", data)
        
        data = data.split(":",3)
        type_ = data[0]
        username = data[1]
        
        if type_ == "CA":
            # Attempting to create account
            
            # print("We are trying to create an account for " + username)
            # print("DATALIST:",data)

            # User already exists
            if username in loginStatus:
                success = "Username-Already-Exists."
                success = Message(username, "SERVER", success)
                client.send(success.encode())
            else:
                # Account is succesffuly created and logged in 
                usernames.append(username)
                clients.append(client)
                clientID[username] = client
                loginStatus[username] = True
                success = "Successful-Account-Creation."
                success = Message(username, "SERVER", success)
                client.send(success.encode())
                onConnection(username)
                client_auth = True
        elif type_ == "L":
            # Attempting to login

            # User does not exist.
            if username not in loginStatus:
                failed = "Login-Failed"
                failed = Message(username,"SERVER", failed)
                client.send(failed.encode())
            # User is already active.
            elif loginStatus[username]:
                # error message that user is already logged in another machine
                active = "Account-Already-Active"
                active = Message(username, "SERVER", active)
                client.send(active.encode())
            else:
                clients.append(client)
                usernames.append(username)
                clientID[username] = client
                loginStatus[username] = True
                success = "Login-Successful."
                success = Message(username, "SERVER", success)
                client.send(success.encode())
                onConnection(username)
                client_auth = True
    # Normal
    while True:
        try:
            header = client.recv(HEADER_LENGTH).decode("utf-8").strip()
            data_length = int(header)
            data = client.recv(data_length)
            # print("HANDLE CLIENT DATA:",data)
            obj = protocol_unpack(data,client)
            protocol_action(obj)

        except:
            # Client Logs out or Crashes
            index = clients.index(client)
            clients.remove(client)
            client.close()
            username = usernames[index]
            # print("USERNAME:",username)
            
            # Check this problem on GRPC 
            if username in loginStatus:
                loginStatus[username] = False
            # print("LOGINSTATUSLIST:",loginStatus)
            # print("USER LOGINSTATUS:", loginStatus[username])
            broadcast(f'{username} has left the chat room!')
            usernames.remove(username)
            break
# Main function to receive the clients connection

def receive():
    while True:
        print('Server is running and listening ...')
        client, address = server.accept()
        print(f'connection is established with {str(address)}')
        print((f'connection is established with CLIENT'))
        print(client)
        # message = f'M:new_user:SERVER:username?'.encode('utf-8')
        # header = f"{len(message) :< {HEADER_LENGTH}}".encode('utf-8')
        # client.send(header+message)
       
        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()

def onConnection(username):
    # print(f'The username of this client is {username}')
    message = f'{username} has connected to the chat room'
    broadcast(message)
    #broadcast(message)
    if username in queuedMessages.keys():
        for message in queuedMessages[username][:]:
            sendToClient(username, message.encode())
            queuedMessages[username].remove(message)

if __name__ == "__main__":
    receive()
