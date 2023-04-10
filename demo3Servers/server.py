import threading
import socket
import sys
from message import Message
from command import Command
import time
import pickle
import os

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# START socket connections to the two other servers in the system.
socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


HEADER_LENGTH = 10
HOST = '10.250.209.143'
PORT = int(sys.argv[1])

# UNIT TEST Init
TESTING_PERSISTENCE = False
chat3SimHist = "(UNIT_TESTS)persistenceTestChats/12342UNITTESTchatHistory.pickle"
UNITTESTVERIFY = {}
with open(chat3SimHist, 'rb') as handle:
        UNITTESTVERIFY = pickle.load(handle)
if sys.argv[2] == "1":
    print("we will be running Unit tests")
    TESTING_PERSISTENCE = True


# Connect sockets to server
myServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
myServer.bind((HOST, PORT))
myServer.listen()


ports = [12340, 12341, 12342]
serverActives = [0,0,0]
ME = ports.index(PORT)
serverActives[ME] = 1


# Stores active socket
clients = []

# Stores active usernames
usernames = [] 

# Stores server connections
servers = []

# Stores all active users {username:socket} pairs
clientID = {}

# Stores if a user is online or not all accounts {username:Boolean}
loginStatus = {}

# The server is always online so users cannot log into the server account
loginStatus['SERVER'] = True


# Stores all messages to offline users {username: Message()}
queuedMessages = {}
queueCounter = 0

# Load queued messages (different case if we are unit testing)
if (TESTING_PERSISTENCE):
    filename = "(UNIT_TESTS)persistenceTestChats/" + str(PORT) + "UNITTESTchatHistory.pickle"
else:
    filename = str(PORT) + "chatHistory.pickle"
if os.path.isfile(filename):
    with open(filename, 'rb') as handle:
        queuedMessages = pickle.load(handle)
    if (TESTING_PERSISTENCE):
        print(bcolors.BOLD + bcolors.OKCYAN + "UNIT TEST: Loads own chat history from disk ✅" + bcolors.ENDC)
else:
    queuedMessages = {}

# Convert queued messages into a structure we can send over the sockets.
pickleMessage = pickle.dumps(queuedMessages)

 # Make the server active.
loginStatus['SERVER'] = True


# Equality checking of message logs -- used for unit tests
def messageLogEquals(d1, d2):
    for u in d1:
        for i in range(len(d1[u])):
            if not Message.equals(d1[u][i], d2[u][i]):
                return False
    return True
    
# Encode the message before sending in sockets
def encoded_message(message):
    message = message.encode('utf-8')
    header = f"{len(message) :< {HEADER_LENGTH}}".encode('utf-8')
    return header+message

# Function sends encoded message to username
def sendToClient(username, message):

    # Creates Message() object
    message = Message(username, "SERVER", message)

    # Finds socket associated with user
    client = clientID[username]

    # Sends encoded message to that user
    client.send(message.encode())

# Function receives data from client
def receiveData(client):
    data = client.recv(HEADER_LENGTH).decode('utf-8')
    data_length = int(data.strip())
    try:
        data = client.recv(data_length).decode('utf-8')
    except:
        print("possible non-string bytes")
        data = client.recv(data_length)
        print(data)
    return data

# Received a message from another server, now act on that message.
def serverProtocol(data):
    print(data)
    dataSplit = data.split(":")
    if dataSplit[0] == "M":
        # we have a message -- add it to the queued messages
        m = Message.createMessageFromBuffer(data)
        m.print()
        queuedMessages[m.recipient].append(m)

        # log
        print("QUEUED messages are: ", queuedMessages)
        with open(filename, 'wb') as handle:
            pickle.dump(queuedMessages, handle, protocol=pickle.HIGHEST_PROTOCOL)

    elif dataSplit[0] == "C":

        # account was created on a leader server -- we need to replicate it here
        username = dataSplit[1]
        loginStatus[username] = False
        queuedMessages[username] = []
        print("usernames: ", loginStatus)

        # log
        with open(filename, 'wb') as handle:
            pickle.dump(queuedMessages, handle, protocol=pickle.HIGHEST_PROTOCOL)

    elif dataSplit[0] == "D":
        # account was deleted on a leader server -- we need to replicate it here

        username = dataSplit[1]
        del loginStatus[username]
        del queuedMessages[username]
        print("ACCOUNT: " + username + " has been attempted to be deleted")
        print("usernames: ", loginStatus)
        print("QUEUED messages are: ", queuedMessages)

        #log
        with open(filename, 'wb') as handle:
                pickle.dump(queuedMessages, handle, protocol=pickle.HIGHEST_PROTOCOL)

def protocol_action(obj):

    # If the object is a Message() then we try to send the message
    if isinstance(obj, Message):

        # If recipient exists -> sends error to client if they do not
        if obj.recipient not in loginStatus:
            # doesNotExist = "The user you are trying to contact does not exist."
            # doesNotExist = Message(obj.sender, "SERVER", doesNotExist)
            # sendToClient(obj.sender, doesNotExist.encode())

            sendToClient(obj.sender, "The user you are trying to contact does not exist.")

        # If recipient is logged-out -> Alerts sender and and queues the message
        elif not loginStatus[obj.recipient]:
            # notlogin = obj.recipient + " is not logged in. But your message will be delivered"
            # notlogin = Message(obj.sender, "SERVER", notlogin)
            # sendToClient(obj.sender,notlogin.encode())

            sendToClient(obj.sender, f"{obj.recipient} is not logged in. But your message will be delivered")

            if obj.recipient not in queuedMessages.keys():
                queuedMessages[obj.recipient] = []
            queuedMessages[obj.recipient].append(obj)

        # Else sends the message to recipient and delivery confirmation to sender
        elif (clientID[obj.recipient] in clients):
            # success = "Your message has successfully delivered."
            # success = Message(obj.sender, "SERVER", success)
            # sendToClient(obj.recipient, obj.encode())
            # sendToClient(obj.sender, success.encode())
            clientID[obj.recipient].send(obj.encode())
            sendToClient(obj.sender, "Your message has successfully delivered.")
    
    # If the object is a Command() then we execute the command
    if isinstance(obj, Command):

        # If Command type is DA -> Delete Account
        if obj.actionType == "DA":
                
            # User must be online execute this Command so no checks are needed

            # Send confirmation to user
            # success = "Account-Successfully-Deleted"
            # success = Message(obj.username, "SERVER", success)
            # sendToClient(obj.username, success.encode())
            sendToClient(obj.username,"Account-Successfully-Deleted")
            message = "D:" + obj.username
            message = encoded_message(message)
            if ME == 0:
                    if serverActives[1] == 1:
                        socket1.send(message)
                    if serverActives[2] == 1:
                        socket2.send(message)
            if ME == 1:
                    if serverActives[0] == 1:
                        socket1.send(message)
                    if serverActives[2] == 1:
                        socket2.send(message)
            if ME == 2:
                    if serverActives[1] == 1:
                        socket1.send(message)
                    if serverActives[0] == 1:
                        socket2.send(message)
           

            # Remove user from loginStatus and clientID list
            del loginStatus[obj.username]
            del clientID[obj.username]

            # Only delete from queued messages if user had queued messages. 
            del queuedMessages[obj.username]
            with open(filename, 'wb') as handle:
                pickle.dump(queuedMessages, handle, protocol=pickle.HIGHEST_PROTOCOL)
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
            # allAccounts = Message(obj.username, "SERVER", allAccounts)
            # sendToClient(obj.username, allAccounts.encode())
            sendToClient(obj.username, allAccounts)


# Protocol unpack returns Message() and Command() from protocol buffers
# Takes a client socket and encoded buffer data
def protocol_unpack(client):
    # Receives bits from client and converts to buffer(encoded)
    data = receiveData(client)
   
    # Buffer data and splits on the colon 
    dataSplit = data.split(":",3)

    # Retrieves type of message/command from buffer data
    type_ = dataSplit[0]

    # If type is M -> create and return Message() object
    if type_ == "M":

        # Return Message()
        return Message.createMessageFromBuffer(data)

    # If type is LA -> create and return Command() object
    elif type_ == "LA":
        
        # Get username from buffer
        username = dataSplit[1]

        # Return Command() with server login status information
        return Command.createCommandFromBuffer(client, loginStatus ,username,type_)

    # If type is DA -> create and return Command() object
    elif type_ == "DA":

        # Get username from buffer
        username = dataSplit[1]

        # Return Command() 
        return Command.createCommandFromBuffer(client, None ,username,type_)
    
# Function sends a message to all active accounts 
def broadcast(message):
    
    # Loops through all active users
    for client in clients:

        # Finds username and creates a message object
        index = clients.index(client)
        username = usernames[index]
        
        # # Sends message to user
        sendToClient(username,message)

# Finds most recent active server (in the order of server 1,2,3)
def find_leader():
    if serverActives[0] == 1:
        return 1
    elif serverActives[1] == 1:
        return 2
    elif serverActives[2] == 1:
        return 3 

# Thread to listen to server connection
def handle_server(server, number):
    global queuedMessages
    global queueCounter

    # Set the server's activity as online (since it is connecting to you).
    serverActives[number - 1] = 1
    
    # See if you need to change leadership
    leader = find_leader()
    print("LEADER IS SERVER", leader)

    # Synchronize queued messages across servers
    qProposal = server.recv(1024)
    qProposal = pickle.loads(qProposal)
    proposalCount = 0
    for x in qProposal:
        if isinstance(qProposal[x], list):
            proposalCount += len(qProposal[x])
    localCount = 0
    for i in queuedMessages:
        if isinstance(queuedMessages[i], list):
            localCount += len(queuedMessages[i])

    print(bcolors.OKBLUE + "SYNCHRONIZING with SERVER" + str(number) + bcolors.ENDC)
    if proposalCount > localCount:
        queuedMessages = qProposal
    
    # Load user acconts from chat logs
    for username in queuedMessages.keys():
        loginStatus[username] = False
    
    print(bcolors.OKBLUE + "<LOADED ACCOUNTS" + bcolors.ENDC)

    queueCounter +=1

    # Unit test -- see if you synchronized to the right log.
    if (TESTING_PERSISTENCE and queueCounter > 1):

        if messageLogEquals(UNITTESTVERIFY, queuedMessages):
            print(bcolors.BOLD + bcolors.OKCYAN + "UNIT TEST: SYNCHRONIZES with MOST UPDATED MESSAGE LOG ✅" + bcolors.ENDC)

        else:
            print(bcolors.FAIL + "UNIT TEST: FAILED TO SYNCHRONIZE WITH MOST UPDATED MESSAGE LOG." + bcolors.ENDC)

    while True:
        try:
            data = receiveData(server)
            serverProtocol(data)
        # This exception handles client crashes and logouts
        except Exception as e:
            # Update leader after the server drops
            serverActives[number - 1] = 0
            leader = find_leader()
            print(bcolors.WARNING + "LEADER IS NOW: "  + str(leader) + bcolors.ENDC )
            server.close()
            return

# Server thread to handle client <-> server communications
def handle_client(client, server1, server2):

    # Displays All accounts and statuses when the client connects


    ## Generate account list
    allAccounts = 'LA|'

    for account in loginStatus:

        # If username is active
        if loginStatus[account]:
            status = 'active'

        # If username is inactive
        else:
            status = 'inactive'

        # Add account status to list with "|", as a divider
        allAccounts += account + " ( " + status + " )" + "|"

    # Remove the last "|" if accounts exists 
    if len(allAccounts) > len("LA|"):
        allAccounts = allAccounts[:-1]
    
    # Sends List of all account statuses to client 
    message = f"M:_:SERVER:{allAccounts}".encode('utf-8')
    header = f"{len(message) :< {HEADER_LENGTH}}".encode('utf-8')
    client.send(header+message)


    ## Account Register/Login Loop

    # Client starts unauthorized
    client_auth = False

    # While user is not authorized attempt to authenticate
    while not client_auth:
         
        # Recieve client Command -- Either type CA (Create Account) or L(Login)
        data = receiveData(client)

        # Split buffer data and extract the username and type that were sent   
        data = data.split(":",3)
        type_ = data[0]
        username = data[1]
        

        # If type is CA -> attempt to create an account with the username
        if type_ == "CA":

            # If username already exists -> Send client error
            if username in loginStatus:
                success = "Username-Already-Exists."
                success = Message(username, "SERVER", success)
                client.send(success.encode())

            # If username doesn't exist -> Send client account creation confirmation
            else:

                # Adds user to the server and logs them in
                usernames.append(username)
                clients.append(client)
                clientID[username] = client
                loginStatus[username] = True
                queuedMessages[username] = []
                
                with open(filename, 'wb') as handle:
                    pickle.dump(queuedMessages, handle, protocol=pickle.HIGHEST_PROTOCOL)

                message = "C:" + username
                message = encoded_message(message)
                socket1.send(message)
                socket2.send(message)

                # log message as well


                sendToClient(username,"Successful-Account-Creation.")

                # Broadcasts new connection and authenticates connection
                onConnection(username)
                client_auth = True


        # If type is L -> attempt to Login in with username
        elif type_ == "L":

            # If user does not exist -> send client login failure message
            if username not in loginStatus:
                failed = "Login-Failed"
                failed = Message(username,"SERVER", failed)
                client.send(failed.encode())

            # If user is already active -> alert client!
            elif loginStatus[username]:
                active = "Account-Already-Active"
                active = Message(username, "SERVER", active)
                client.send(active.encode())

            # If username exists and is not active -> log user in
            else:
                # Log user in
                clients.append(client)
                usernames.append(username)
                clientID[username] = client
                loginStatus[username] = True

                # Send confirmation message
                sendToClient(username,"Login-Successful.")

                # Broadcast connection and deliver messages and authenticate client
                onConnection(username)
                client_auth = True

    # Receives buffers from client and applies wire protocol
    while True:
        try:

            # Applies wire protocol to buffer -> returns a Message() or Command() objects
            obj = protocol_unpack(client)
            if isinstance(obj, Message):
                queuedMessages[obj.recipient].append(obj)
                with open(filename, 'wb') as handle:
                    pickle.dump(queuedMessages, handle, protocol=pickle.HIGHEST_PROTOCOL)
                if ME == 0:
                    if serverActives[1] == 1:
                        socket1.send(obj.encode())
                    if serverActives[2] == 1:
                        socket2.send(obj.encode())
                if ME == 1:
                    if serverActives[0] == 1:
                        socket1.send(obj.encode())
                    if serverActives[2] == 1:
                        socket2.send(obj.encode())
                if ME == 2:
                    if serverActives[1] == 1:
                        socket1.send(obj.encode())
                    if serverActives[0] == 1:
                        socket2.send(obj.encode())
            # Applies an action to the object
            protocol_action(obj)


        # This exception handles client crashes and logouts
        except:

            # Removes client from active user lists
            index = clients.index(client)
            clients.remove(client)

            # Get clients username and then remove them from active user lists
            username = usernames[index]
            usernames.remove(username)

            
            # Only change loginStatus is user account isn't deleted
            if username in loginStatus:
                loginStatus[username] = False

            # Broadcast to everyone that the client disconnected
            broadcast(f'{username} has left the chat room!')
            break


# receive() listens for client and server connections and starts new threads when found
def receive():
    # When server starts
    print('Openning connection, running, and listening ...')

    while True:
        # Accepts new client on client connection
        client, address = myServer.accept()
        # Logs client connection information
        print(f'connection is established with: {str(address)}')
        connection = ''
        if str(address[1]) == '12349' or str(address[1]) == '12346':
            connection = "SERVER1"
            # Open up receivng thread with Server 1
            servers.append(client)
            thread = threading.Thread(target=handle_server, args=(client,1))
            thread.start()
        elif str(address[1]) == '12350' or str(address[1]) == '12347':
            connection = "SERVER2"
            # Open up receiving thread with Server 2
            servers.append(client)
            thread = threading.Thread(target=handle_server, args=(client,2))
            thread.start()
        elif str(address[1]) == '12351' or str(address[1]) == '12348':
            connection = "SERVER3"
            # Open up receiving thread with Server 3
            servers.append(client)
            thread = threading.Thread(target=handle_server, args=(client,3))
            thread.start()
        else:
            # Open up a receiving thread with the client
            connection = "CLIENT"
            thread = threading.Thread(target=handle_client, args=(client, servers[0], servers[1]))
            thread.start()
        
        print((f'connection is established with :{connection}'))




# onConnection() broadcasts a username and dequeues their messages
def onConnection(username):

    # User connection broadcast
    message = f'{username} has connected to the chat room'
    broadcast(message)

    # Dequeing of stored user messages
    if username in queuedMessages.keys():
        for message in queuedMessages[username][:]:

            # Finds socket associated with user
            client = clientID[username]

            # Sends encoded message to that user
            client.send(message.encode())

            # commenting to send all of the chat history
            #queuedMessages[username].remove(message)

if __name__ == "__main__":

    time.sleep(4)

    socket1.bind((HOST, PORT + 6))
    socket2.bind((HOST, PORT + 9))
    # attempt to connect to the three servers
    print("MY PORT IS ", PORT)
    if PORT == 12340:
        socket1.connect((HOST, 12341))
        socket2.connect((HOST, 12342))
    elif PORT == 12341:
        socket1.connect((HOST, 12340))
        socket2.connect((HOST, 12342))
    elif PORT == 12342:
        socket1.connect((HOST, 12341))
        socket2.connect((HOST, 12340))
    socket1.send(pickleMessage)
    socket2.send(pickleMessage)
    if (TESTING_PERSISTENCE):
        print(bcolors.BOLD + bcolors.OKCYAN + "UNIT TEST: Sends chat history to other servers ✅" + bcolors.ENDC)

    receive()
