# CS 3357 Assignment 3 Matthew Cheverie 251098050
# This file runs the server for this multi client chat application. Multiple clients are able to connect to the server
# via multiplexing from the select package.  The sys package is used to write and read data to and from the terminal
# as well as shutting down the program. The signal package is used to handle CTRL C inputs. The server also keeps track
# of followed terms for all users as well as handles all commands send from the users.
import sys
from socket import *
import select
import signal
import string

# Declare some administrative variables

HOST = 'localhost'  # Constant that contains the name of the host
socketList = []  # List for the sockets
users = {}  # Dictionary pairing usernames to their sockets. The username is the key
followDict = {}  # Dictionary paring usernames to lists of followed terms and users
PUNC = string.punctuation  # Declare constant for punctuation for right stripping
PUNC_MISSING_AT = PUNC.replace("@",
                               "")  # Create a variable to contain all punctuation except @. Used for left stripping


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
    sendServerMessage(serverSock, msg)
    try:
        serverSock.close()
    except Exception as e:
        print("The server socket could not be closed.")
        print(e)
    print("Server successfully closed! Exiting program")
    sys.exit(0)


# This function will get a clients username by referencing the socket value stored.
# Parameters dict - the dictionary, value - the value associated with the key
def getKeyByValue(dict, value):
    keyList = list(dict.keys())
    valList = list(dict.values())

    position = valList.index(value)
    return keyList[position]


# This function sends a file to a user based on the terms specified in the header. It will send a give file to all users
# in the terms or to any user who follows a word in the terms list.
# parameters: Socket - the socket from the user who sent the file, header - the file header to be sent,
# headerList- the list created from splitting the header, terms - the terms from the request command
def sendBasedOnTerms(sock, header, headerList, terms):
    termList = terms.split(" ")  # Create a list of all words in the terms

    # IF the file to be sent is a text file
    if headerList[0].strip() == "TEXT":
        # Keep track of a list of sockets that we have already sent the file too. Ensures that file only gets sent
        # To the requried user once
        alreadySent = []

        # This nested for loop will check every word in the terms list and see if it belongs to the followed list for
        # every uesr. If So, send the packets to them and add their socket to the already sent list.
        for user in users:
            for word in termList:
                word = word.lstrip(PUNC_MISSING_AT)
                word = word.rstrip(PUNC)
                if word in followDict[user] and users[user] not in alreadySent and users[user] != sock:
                    count = 0
                    sendText = open(headerList[1], "r")
                    sendText.seek(0)
                    users[user].send(header.encode())
                    while count <= int(headerList[3]):
                        print("Sending packets to " + user)
                        data = sendText.read(1024).encode()
                        if not data:
                            break
                        users[user].send(data)
                        count += len(data)
                        alreadySent.append(users[user])
                    print("Sent text file to " + user)
    # Same process as above excpet for binary files
    else:
        alreadySent = []
        for user in users:
            for word in termList:
                word = word.lstrip(PUNC_MISSING_AT)
                word = word.rstrip(PUNC)
                if word in followDict[user] and users[user] not in alreadySent and users[user] != sock:
                    count = 0
                    sendFile = open(headerList[1], "rb")
                    sendFile.seek(0)
                    users[user].send(header.encode())
                    while count <= int(headerList[3]):
                        print("Sending packets to " + user)
                        data = sendFile.read(1024)
                        if not data:
                            break
                        users[user].send(data)
                        count += len(data)
                    alreadySent.append(users[user])
                    print("Sent binary file to " + user)
                    # sendFile.close()
    successMessage = "File Sent!"
    sock.send(successMessage.encode())


# Function to send messages sent from other users to users who are following terms in their message. Works similar to
# function above
# Params: socket - the socket of the user sending the message, message - the message to be sent
def sendMsg(sock, message):
    wordList = message.split(' ')
    alreadySent = []
    for word in wordList:
        word = word.lstrip(PUNC_MISSING_AT)
        word = word.rstrip(PUNC)
        for user in users:
            if word in followDict[user] and users[user] not in alreadySent and users[user] != sock:
                users[user].send(message.encode())
                alreadySent.append(users[user])


# This function will try send a message to all active sockets accept the one passed in and the server socket. If an
# exception is thrown, this means the socket is not active. The socket will be removed from the active socket list and
# the user will be removed from the user dictionary
def sendServerMessage(sock, message):
    for socket in socketList:
        if socket != serverSock and socket != sock:
            try:
                socket.send(message.encode())
            except:
                socket.close()
                socketList.remove(socket)
                dictKey = getKeyByValue(users, socket)
                followDict.pop(dictKey)
                users.pop(dictKey)


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
    name = registerList[1]
    # If the registration message is invalid
    if len(registerList) != 3:
        error400msg = "400 Invalid registration for user " + name
        print(error400msg)
        socket.send(error400msg.encode())
        return False
    if name == 'all':
        error400msg = "400 Invalid registration for user " + name + ". All is reserved username which cannot be taken."
        print(error400msg)
        socket.send(error400msg.encode())
    # If there is a client already registered with that name
    elif name in users:
        error401msg = "401 Client already registered for user " + name
        print(error401msg)
        socket.send(error401msg.encode())
        return False

    # If the registration was successful, send message to user that registration was successful. Notify all other clients
    # that a new user has joined the server. Add the user to the dictionary
    else:
        success200msg = "200 Registration successful for user " + name
        print(success200msg)
        userAt = '@' + name
        users[name] = socket
        followDict[name] = ['@all', userAt]
        socket.send(success200msg.encode())
        sendToAllmsg = "Client @" + name + " has joined the server! Say hi!!\n"
        sendServerMessage(socket, sendToAllmsg)
        return True


# Function to get and return the size in bytes of any passed in file
def getFileSize(file):
    file.seek(0, 2)
    size = file.tell()
    return size


# Function for handling commands from any given user.
# Parameters: command - the command from the user, socket - the socket from which the command was sent from
def commandHandler(command, socket):
    commandArgs = command.split(' ')  # Create a list of command arguments
    user = getKeyByValue(users, socket)  # get the username based on the socket

    # IF the command is !list, send a comma seperated list of all active users to the lcient
    if command.strip() == '!list':
        theUsers = getActiveUsers(users)
        csList = ", ".join(theUsers)
        sendM = "The active users are: " + csList
        socket.send(sendM.encode())

    # If the command is !exit, send a disconnect exit request to the client for processing. Remove the user from the
    # dictionary of users and dictionary of followed items. Send a message to all users displaying remaing active users.
    # Remove the socket from list of sockets and close that socket
    if command.strip() == '!exit':
        exitMes = "DISCONNECT EXIT"
        socket.send(exitMes.encode())
        followDict.pop(user)
        users.pop(user)
        activeUsers = getActiveUsers(users)
        activeUserMessage = "The remaining active users are " + str(activeUsers) + ".\n"
        sendServerMessage(socket, activeUserMessage)
        # Remove the socket from the list of active sockets and close that socket
        socketList.remove(socket)
        socket.close()

    # Diplays a list of all followed items for the user
    elif command.strip() == '!follow?':
        userFollow = ", ".join(followDict[user])
        message = "Your followed items are: " + userFollow
        socket.send(message.encode())

    # adds an entry to the list for the user in the follow dictionary if they are not already following that item
    elif commandArgs[0].strip() == '!follow':
        if commandArgs[1].strip() in followDict[user]:
            message = "You already follow " + commandArgs[
                1].strip() + ". Cannot follow an item that is already followed"
            socket.send(message.encode())
        else:
            followDict[user].append(commandArgs[1].strip())
            message = "You are now following " + commandArgs[1].strip()
            socket.send(message.encode())

    # Unfollows a given term if the user is following it. Cannot unfollow the all user or themselves.
    elif commandArgs[0].strip() == '!unfollow':
        userAt = '@' + user
        if commandArgs[1].strip() not in followDict[user]:
            message = "Cannot unfollow an item that you are not following!!!"
            socket.send(message.encode())
        elif commandArgs[1].strip() == '@all' or commandArgs[1].strip() == userAt:
            message = "Cannot unfollow yourself or the all user!"
            socket.send(message.encode())
        else:
            followDict[user].remove(commandArgs[1].strip())
            message = "Successfully unfollowed " + commandArgs[1].strip()
            socket.send(message.encode())
    # IF the user wants to send a file, this command will request the file from the user. It will then store it on the
    # Server for further processing.
    elif commandArgs[0].strip() == '!attach':
        terms = ' '.join(commandArgs[2:])
        reqMessage = "REQUEST " + commandArgs[1]
        socket.send(reqMessage.encode())

        if commandArgs[1].endswith("txt"):
            status = "HEADER_SUC"
            count = 0
            try:
                header = socket.recv(1024).decode()
            except Exception as e:
                print(e)
                status = "HEADER_FAIL"
                print(status)
            if status == "HEADER_SUC":
                headerList = header.split("_")
                try:
                    serverFile = open(headerList[1], "w+")
                except Exception as e:
                    print("The File could not be opened. " + e)
                while count < int(headerList[3]):
                    data = socket.recv(1024)
                    if data.decode() == "":
                        break
                    serverFile.write(data.decode())
                    serverFile.flush()
                    count += len(data)
                print("File received from: " + headerList[2])
                sendBasedOnTerms(socket, header, headerList, terms)
                serverFile.close()
        else:
            status = "HEADER_SUC"
            count = 0
            try:
                header = socket.recv(1024).decode()
            except Exception as e:
                print(e)
                status = "HEADER_FAIL"
                print(status)
            if status == "HEADER_SUC":
                headerList = header.split("_")
                try:
                    serverFile = open(headerList[1], "wb+")
                except Exception as e:
                    print("The File could not be opened. " + e)
                while count < int(headerList[3]):
                    data = socket.recv(1024)
                    if not data:
                        break
                    serverFile.write(data)
                    serverFile.flush()
                    count += len(data)
                print("File received from: " + headerList[2])
                sendBasedOnTerms(socket, header, headerList, terms)
                serverFile.close()
            print("File received")


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
                data = socket.recv(1024)

                # If no data is recived, that means the user from which the socket is connected to is offline
                if not data:
                    dictKey = getKeyByValue(users, socket)
                    leavingMessage = "Client @" + dictKey + " is offline\n"
                    print(leavingMessage)
                    sendServerMessage(socket, leavingMessage)  # Send message to all users that the person is offline
                    followDict.pop(dictKey)
                    users.pop(dictKey)
                    socketList.remove(socket)
                    socket.close()

                # If the data recvieed is a disconnect message, start the disconnect process
                elif data.decode().startswith('DISCONNECT'):
                    # This Block notifies users that the client has left the server
                    message = data.decode()
                    splitMessage = message.split(' ')
                    userDisconnect = splitMessage[1]
                    userMessage = "Client " + userDisconnect + " has left the server."
                    print(userMessage)
                    sendServerMessage(socket, userMessage)

                    # This removes the user from the dictionary of active users and lets everyone know who is active
                    followDict.pop(userDisconnect)
                    users.pop(userDisconnect)
                    activeUsers = getActiveUsers(users)
                    activeUserMessage = "The remaining active users are " + str(activeUsers) + ".\n"
                    sendServerMessage(socket, activeUserMessage)

                    # Remove the socket from the list of active sockets and close that socket
                    socketList.remove(socket)
                    socket.close()
                elif data.decode().startswith('!'):
                    command = data.decode()
                    commandHandler(command, socket)

                # This loop gets triggered when a user sends a normal message
                else:
                    message = data.decode()
                    dictKey = getKeyByValue(users, socket)
                    print('Recieved message from @' + dictKey + ': ' + message.strip())
                    sendMsg(socket, message)
            # The except will be triggered if the socket.recv() throws an excepion. Ususally happens if someone crashes
            except Exception as e:
                print(e)
                dictKey = getKeyByValue(users, socket)
                leavingMessage = "Client " + dictKey + " has left the conversation unexpectedly\n"
                print(leavingMessage)
                sendServerMessage(socket, leavingMessage)
                followDict.pop(dictKey)
                users.pop(dictKey)
                socketList.remove(socket)
                socket.close()
                continue
