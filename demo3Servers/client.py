# Import modules used
import sys
import threading
import socket
import os
import signal
from message import Message

# Constants used in text styling
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

# Creates an encoded bitstring from a message using our wire protocol
def encoded_message(message):
    message = message.encode('utf-8')
    header = f"{len(message) :< {HEADER_LENGTH}}".encode('utf-8')
    return header+message

# Defined header length throughout wire protocol
HEADER_LENGTH = 10
HOST = '10.250.209.143'

# Create a socket and connect to the server
client1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client1.connect((HOST, 12340))

# Keep track of leader server
SERVERSTATE = 1


auth = False
username = ''

try:
    # Retrieves list from server of all existing accounts
    header = client1.recv(HEADER_LENGTH).decode('utf-8').strip()
    data_length = int(header)
    data = client1.recv(data_length).decode('utf-8')

    # Displays all accounts with their activity status
    allAccounts = data.split("|")[1:]
    print(bcolors.OKGREEN + "The server holds the following accounts." + bcolors.ENDC)
    for account in allAccounts:
        print(" -- > " + account)
    
    
    # goBack loop lets user reselect if they want to login or create an account
    goBack = True
    while goBack:
        
        # Asks user if they would like to login or create an account
        command = input("Type " + bcolors.BOLD + "C" + bcolors.ENDC + " to create an account. Type " + bcolors.BOLD + "L" + bcolors.ENDC + " to login in." )
        
        # Reprompt if user gives invalid answer
        while command != "C" and command != "L":
            print("Please select either C or L\n")
            command = input("Type " + bcolors.BOLD + "C" + bcolors.ENDC + " to create an account. Type " + bcolors.BOLD + "L" + bcolors.ENDC + " to login in." )


        # Authentication loop only broken if user goes back or is authenticated
        while not auth:

            # Asks for username and gives option to go back 
            print("Usernames must be alphanumeric characters.\n(Type "+bcolors.BOLD+"!"+bcolors.ENDC+" to go back)")
            username = input("Please enter a username:")

            # If user wants to create an account and submits a real username
            if command == "C" and username != "!":
                
                # Sends Create account request to server
                request_message = f"CA:{username}"
                request_message = encoded_message(request_message)
                client1.send(request_message)

                # Awaits and receives server confirmation
                header = client1.recv(HEADER_LENGTH).decode('utf-8')
                confirmation_length = int(header.strip())
                confirmation = client1.recv(confirmation_length).decode('utf-8')
                
                # Takes the confirmation message only
                confirmation = confirmation.split(":",3)[3]
                
                # Checks if request is successful
                if confirmation == "Successful-Account-Creation.":
                    
                    # User is authorized
                    auth = True
                    goBack = False
                    
                    # Print confirmation message
                    print(bcolors.OKGREEN + confirmation + bcolors.ENDC)

                else:

                    # Print confirmation message
                    print(bcolors.FAIL + confirmation + bcolors.ENDC)

            # If user submits a real username and command type is L
            elif username != "!":
                
                # Send Login request to server
                request_message = f"L:{username}"
                request_message = encoded_message(request_message)
                client1.send(request_message)

                # Awaits and recieves confirmation from server
                header = client1.recv(HEADER_LENGTH).decode('utf-8').strip()
                confirmation_length = int(header.strip())
                confirmation = client1.recv(confirmation_length).decode('utf-8')

                # Retrieve confirmation message
                confirmation = confirmation.split(":",3)[3]

                # Checks if request is successful
                if confirmation == "Login-Successful.":
                    # User is authorized
                    auth = True
                    goBack = False
                    
                    # Print confirmation message
                    print(bcolors.OKGREEN + confirmation + bcolors.ENDC)

                else:
                    
                    # Print confirmation message
                    print(bcolors.FAIL + confirmation + bcolors.ENDC)
            
            # If username is !, break out of auth loop and reprompt commands
            else:
                break            

    # Thread that listens for communications from the server
    def client_receive(connection):
        global SERVERSTATE
        while True:
            try:

                # Receives data sent by server
                data_header = connection.recv(HEADER_LENGTH).decode('utf-8')
                data_length = int(data_header.strip())
                data = connection.recv(data_length).decode('utf-8')

                # Converts received data into a message object
                data = Message.createMessageFromBuffer(data)

                # Checks if message sender is SERVER
                if (data.sender == "SERVER"):
                    
                    # If message object doesn't encode properly
                    if data.data[0] == "<":
                        continue

                    # If SERVER is sending a list of active accounts
                    if data.data[0:3] == "LA|":

                        # Unpacks the sent list 
                        allAccounts = data.data.split("|")[1:]
                        
                        # Prints list
                        print(bcolors.OKGREEN + "The server holds the following accounts." + bcolors.ENDC)
                        for account in allAccounts:
                            print(" -- > " + account)

                    # If SERVER Confirms account is successfully deleted
                    elif data.data == "Account-Successfully-Deleted":

                        # Print message to console
                        print("Your account has been deleted. Your client connection will end. Bye, Bye")
                        print(bcolors.BOLD + bcolors.FAIL + "EXITING CLIENT PROGRAM." + bcolors.ENDC)
                        
                        # Exits terminal and closes socket
                        os.kill(os.getpid(), signal.SIGINT)
                    
                    # If SERVER cannot find and delete account 
                    elif data.data == "Account-Does-Not-Exist":
                        print(bcolors.FAIL + data.data + bcolors.ENDC)

                    # If SERVER is sending a broadcast message
                    else:
                        print(bcolors.OKCYAN + "[" + data.sender + "] " + bcolors.ENDC + data.data)


                # If the message is sent from another user
                if data.sender != "SERVER":
                    print(bcolors.OKCYAN + "[" + data.sender + "] " + bcolors.ENDC + data.data)

            # Any general errors are caught here
            except Exception as e:

                print(bcolors.WARNING +'SERVER DROPPED. RECONNECTING. PRESS ENTER. ' + bcolors.ENDC)
                connection.close()
                SERVERSTATE = SERVERSTATE + 1
                sys.exit()


    # Thread that sends authenticated communication to the server
    def client_send(connection, state):
        global SERVERSTATE
        while True:
            if state != SERVERSTATE:
                sys.exit()
            # Asks user for input
            inp = input(bcolors.BOLD +"COMMANDS" + bcolors.ENDC + ": " + bcolors.BOLD + "\n" +"LA" + bcolors.ENDC + " - List accounts. "+ bcolors.BOLD + "\n" + "USERNAME-> MESSAGE" + bcolors.ENDC+ " - Send USERNAME MESSAGE." + "\n" + bcolors.BOLD + "DA" + bcolors.ENDC + " - Delete your account."+"\n" + bcolors.BOLD + "Q" + bcolors.ENDC + " - Quit client program."+"\n")
            
            # If user enters nothing
            if inp == "":
                print(bcolors.WARNING + "Empty input" + bcolors.ENDC)
            
            # User enters something
            else:

                # If input is not a message
                if "->" not in inp:

                    # Check if it List Accounts request
                    if inp == "LA":

                        # Sends List Accounts request
                        message = f"LA:{username}"
                        message = encoded_message(message)
                        connection.send(message)
                        
                    # Check if it is a Delete Account request
                    elif inp == "DA":
                        
                        # Sends delete account request with authorized username
                        message = f"DA:{username}"
                        message = encoded_message(message)
                        connection.send(message)

                    # Check if the user is trying to quit the program
                    elif inp == "Q":
                        
                        # Prints exit message
                        print(bcolors.BOLD + bcolors.FAIL + "EXITING CLIENT PROGRAM." + bcolors.ENDC)
                        
                        # Exits terminal and closes socket
                        os.kill(os.getpid(), signal.SIGINT)
                        break

                    # User submitted invalid message syntax
                    else:
                        # Prints syntax warning message
                        print(bcolors.WARNING + "NEED TO SPECIFY USER. Correct usage: USER-> Message." + bcolors.ENDC)
                
                # User submitted valid message syntax
                else:
                    # Breaks input into recipient and message based on "->"
                    inputList = inp.split("->")
                    recipient = inputList[0]
                    message = inputList[1]

                    # Creates a message object
                    message = Message(recipient, username, message)
                    message = message.encode()

                    # Sends message to server
                    connection.send(message)


            

    receive_thread1 = threading.Thread(target=client_receive, args=[client1])
    receive_thread1.start()

    send_thread1 = threading.Thread(target=client_send, args= [client1, 1])
    send_thread1.start()

    # DETECTED DROP IN SERVER 1
    while receive_thread1.is_alive() or send_thread1.is_alive():
        x = 3
    
    server2GoesThrough = True

    # TRY TO CONNECT TO SERVER 2
    try:

        client2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client2.connect((HOST, 12341))
        request_message = f"L:{username}"
        request_message = encoded_message(request_message)
        client2.send(request_message)

        receive_thread2 = threading.Thread(target=client_receive, args=[client2])
        receive_thread2.start()

        send_thread2 = threading.Thread(target=client_send, args= [client2, 2])
        send_thread2.start()

    except:
        server2GoesThrough = False
        SERVERSTATE = 3
        print("server 2 must have been dropped...")
    
    
    if server2GoesThrough:
        while receive_thread2.is_alive() or send_thread2.is_alive():
            x = 3

    # SERVER 2 HAS BEEN DROPPED OR NOT ABLE TO CONNECT

    # CONNECT TO SERVER 3
    client3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client3.connect((HOST, 12342))
    request_message = f"L:{username}"
    request_message = encoded_message(request_message)
    client3.send(request_message)

    receive_thread3 = threading.Thread(target=client_receive, args=[client3])
    receive_thread3.start()

    send_thread3 = threading.Thread(target=client_send, args= [client3, 3])
    send_thread3.start()
 

# If user exits with ^C it is caught here
except KeyboardInterrupt:
    print(bcolors.BOLD + bcolors.FAIL + "EXITING CLIENT PROGRAM." + bcolors.ENDC)
    
