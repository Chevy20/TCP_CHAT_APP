# CS 3357 Assignment 1 Matthew Cheverie 251098050
# This file runs the server for this multi client chat application. Multiple clients are able to connect to the server
# via multiplexing from the select package.  The sys package is used to write and read data to and from the terminal
# as well as shutting down the program. The signal package is used to handle CTRL C inputs
import sys
from socket import *
import select
import signal

# Declare some administrative variables

HOST = 'localhost'  # Constant that contains the name of the host
socketList = []  # List for the sockets
users = {}  # Dictionary pairing usernames to their sockets. The username is the key


# Function that returns all the active users in the server. It works by creating a list of all the keys (usernames) in
# dictionary.
# Parameters: dict - the dictionary that holds the the usernames and their sockets
def getActiveUsers(dict):
    activeUsers = list(dict.keys())
    return activeUsers


# Function that will handle control c inputs from the server. It will print a message to the users saying the server will
# shut down. It will then send a disconnect command to all the users, which will disconnect all clients from the server.
# It will then shut down the server
# Parameters: sig - the signal received, frame - the terminal from which the command came
def signalHandler(sig, frame):
    print("CTRL C dectected. The chat server will be shut down and all users will be notified")
    msg = "DISCONNECT CHAT/1.0"
    sendMsg(serverSock, msg)
    try:
        serverSock.close()
    except Exception as e:
        print("The server socket could not be closed.")
        print(e)
    print("Server successfully closed! Exiting program")
    sys.exit(0)


# This function will an entry from the dictionary based on the given key passed in. It will then return the dictionary
# Parameters: d - the dictionary, key - the key used to reference the entry to be deleted
def removeKey(d, key):
    r = dict(d)
    del r[key]
    return r


# This function will get a clients username by referencing the socket value stored.
# Parameters dict - the dictionary, value - the value associated with the key
def getKeyByValue(dict, value):
    keyList = list(dict.keys())
    valList = list(dict.values())

    position = valList.index(value)
    return keyList[position]


# This function will try send a message to all active sockets accept the one passed in and the server socket. If an
# exception is thrown, this means the socket is not active. The socket will be removed from the active socket list and
# the user will be removed from the user dictionary
def sendMsg(sock, message):
    for socket in socketList:
        if socket != serverSock and socket != sock:
            try:
                socket.send(message.encode())
            except:
                socket.close()
                socketList.remove(socket)
                dictKey = getKeyByValue(users, socket)
                users = removeKey(users, dictKey)


# This function will attempt to register the user in the client dictionary. It will receive a message from the socket
# passed which will contain the register message in the form REGISTER username chat/1.0. Refer to if statements for
# explanations.
def registerUser(socket):
    username = socket.recv(4096).decode()
    try:
        registerList = username.split(' ')
    # If there are no spaces in the register message
    except:
        error400msg = "400 Invalid registration for user " + registerList[1]
        print(error400msg)
        socket.send(error400msg.encode())
        return False

    # If the registration message is invalid
    if len(registerList) != 3:
        error400msg = "400 Invalid registration for user " + registerList[1]
        print(error400msg)
        socket.send(error400msg.encode())
        return False

    # If there is a client already registered with that name
    if registerList[1] in users:
        error401msg = "401 Client already registered for user " + registerList[1]
        print(error401msg)
        socket.send(error401msg.encode())
        return False

    # If the registration was successful, send message to user that registration was successful. Notify all other clients
    # that a new user has joined the server. Add the user to the dictionary
    else:
        success200msg = "200 Registration successful for user " + registerList[1]
        print(success200msg)
        users[registerList[1]] = socket
        socket.send(success200msg.encode())
        sendToAllmsg = "Client @" + registerList[1] + " has joined the server! Say hi!!\n"
        sendMsg(socket, sendToAllmsg)
        return True


# Where the program starts - Setting up server
serverSock = socket(AF_INET, SOCK_STREAM)  # create the server socket
serverSock.bind((HOST, 0))  # Bind it to localhost and port 0, which will choose a port at random
serverSock.listen()  # listen for new connections
socketList.append(serverSock)  # Add the server socket to the list of active sockets
print('The Server is ready to connect to clients on port '
      + str(serverSock.getsockname()[1]))  # Print a message saying which port clients need to connect to

# This while loop will run the server
while True:
    signal.signal(signal.SIGINT, signalHandler)  # Listen for Control C inputs

    # Use select to handle mutiple clients and actions at the same time
    read_ready, write_ready, exception = select.select(socketList, [], [])

    # This For loop will process all the sockets that are trying to communicate with the server socket
    for socket in read_ready:

        # This if statement means that a new client is trying to connect with the server
        if socket == serverSock:
            newConnection, address = serverSock.accept()  # Accept the connection
            print("Connection has been esstablished with a client at address (%s,%s)" % address)
            if registerUser(newConnection) is True:  # If the user can be registered, add its socket to list of sockets
                socketList.append(newConnection)
        # This statement handles any socket that is trying to send a message
        else:
            # Try to receive data from the socket
            try:
                data = socket.recv(4096)

                # If no data is recived, that means the user from which the socket is connected to is offline
                if not data:
                    dictKey = getKeyByValue(users, socket)
                    leavingMessage = "Client @" + dictKey + " is offline\n"
                    print(leavingMessage)
                    sendMsg(socket, leavingMessage)     #Send message to all users that the person is offline
                    users = removeKey(users, dictKey)
                    socketList.remove(socket)
                    socket.close()

                # If the data recvieed is a disconnect message, start the disconnect process
                elif data.decode().startswith('DISCONNECT'):

                    #This Block notifies users that the client has left the server
                    message = data.decode()
                    splitMessage = message.split(' ')
                    userDisconnect = splitMessage[1]
                    userMessage = "Client " + userDisconnect + " has left the server."
                    print(userMessage)
                    sendMsg(socket, userMessage)

                    # This removes the user from the dictionary of active users and lets everyone know who is active
                    users = removeKey(users, userDisconnect)
                    activeUsers = getActiveUsers(users)
                    activeUserMessage = "The remaining active users are " + str(activeUsers) + ".\n"
                    sendMsg(socket, activeUserMessage)

                    # Remove the socket from the list of active sockets and close that socket
                    socketList.remove(socket)
                    socket.close()

                # This loop gets triggered when a user sends a normal message
                else:
                    message = data.decode()
                    dictKey = getKeyByValue(users, socket)
                    print('Recieved message from @' + dictKey + ': ' + message.strip())
                    sendMsg(socket, message)
            # The except will be triggered if the socket.recv() throws an excepion. Ususally happens if someone crashes
            except:
                dictKey = getKeyByValue(users, socket)
                leavingMessage = "Client " + dictKey + " has left the conversation unexpectedly\n"
                print(leavingMessage)
                sendMsg(socket, leavingMessage)
                users = removeKey(users, dictKey)
                socketList.remove(socket)
                socket.close()
                continue
