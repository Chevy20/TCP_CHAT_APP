# CS 3357 Assignment 3 Matthew Cheverie 251098050
# This file runs the chat client for the user. It uses select to handle multiplexing. Sys for dealing with the terminal.
# uses urlparse to parse through the command line arguments. Uses signal to handle control C inputs. Users can follow
# other users and terms. They can unfollow terms and users as well. Files can also be sent. This works by sending file
# to server and creating a copy stored on the server. It then gets all the users it needs to send it to and reads data
# from file stored on server and sends it to all required users.
from socket import *
import select
import sys
from urllib.parse import urlparse
import signal
import os


# Function that will handle control c inputs from the server. It will print a message saying that the client will be
# Disconnected. It will send the disconnect command to the server. It will then try to close the socket. IF successful,
# The client will close, if not print the exception
# Parameters: sig - the signal received, frame - the terminal from which the command came
def signalHandler(sig, frame):
    print("CTRL C dectected. The user @" + username + " will be disconnected")

    msg = "DISCONNECT " + username + " CHAT/1.0"
    clientSock.send(msg.encode())
    try:
        clientSock.close()
    except Exception as e:
        print(e)
    print("Client successfully closed! Exiting program")
    sys.exit(0)


# This function will just prompt the user with a > symbol to type
def prompt():
    printLine = "\n>"
    sys.stdout.write(printLine)
    sys.stdout.flush()


# This function will get the response from the server to the request to register message. If it was successful, the
# Client will continue to run. If not print an error message and close the client
def regUserWithClient(cSock):
    message = cSock.recv(4096).decode()
    if message.startswith('2'):
        print(message)
    elif message.startswith('4'):
        print(message + ' The system will now exit!')
        cSock.close()
        sys.exit()


# This is the entry point
# If there are more than 3 command line args, print an error message and exit
if len(sys.argv) != 3:
    print("Invalid format for commandline args. System will now exit")
    sys.exit(-1)

username = sys.argv[1]  # Get the username as the second command line arg passed in

# try to parse the url style command line arg (cla).
# If cannot be done, it was not formatted properly. Print error and exit
try:
    cla = urlparse(sys.argv[2])
except:
    print("Invalid format for commandline args. System will now exit")
    sys.exit(-1)

# Get the host and the port from command line args
host = str(cla.netloc.split(':')[0])
port = int(cla.netloc.split(':')[1])

# Create a socket for the client
clientSock = socket(AF_INET, SOCK_STREAM)

# Try to connect to the server. If it cannot, print excepetion and exit
try:
    clientSock.connect((host, port))
except Exception as e:
    print(e)
    sys.exit()

# Let the user know they have been connected to the host and awaiting registration
print("Connected to host! Awaiting registration")
regMes = "REGESTER " + username + " CHAT/1.0"  # create registration command to server
clientSock.send(regMes.encode())  # send reg command to server
regUserWithClient(clientSock)  # Get response from server and continue if successful, exit if not
prompt()  # Write the prompt for the terminal, where the user will enter text

socketList = [sys.stdin, clientSock]  # Create the socket list for this client

# This will be what runs when the user is connected and registered with the server

while True:
    signal.signal(signal.SIGINT, signalHandler)  # Look for Control C Inputs
    read_list, write_list, exception_list = select.select(socketList, [], [])  # Use select to handle multiple sockets

    # This loop will deal with each socket that needs to be processed
    for sock in read_list:

        # This will be when a message is sent to the client, either from another user or the server
        if sock == clientSock:
            data = sock.recv(1024)

            # If no data is recived and error occurred and the client is disconnected
            if not data:
                print('Disconnected!!')
                clientSock.close()
                sys.exit()

            # If a server disconnect message is received, shut down this client and exit the system
            if data.decode() == "DISCONNECT CHAT/1.0":
                print("Server is shutting down! All clients will be disconnected")
                clientSock.close()
                sys.exit(0)

            # The message displayed when the server confirms that the !exit command was excetured
            if data.decode() == "DISCONNECT EXIT":
                print("Disconnected from server! .... Exiting the program. \n Goodbye!")
                clientSock.close()
                sys.exit(0)

            # This will get triggered when the server sends a request for a file.
            if data.decode().startswith("REQUEST"):
               # Get the request from the server, split into a list. Fileneame contained in index 1
                req = data.decode().split(" ")
                filesend = None  # initialize varible to none, make its scope outside of both if statements so it can be used between varibles
                count = 0        # set count for bytes read to 0
               # IF the requested file is a text file
                if req[1].endswith("txt"):
                    flag = 1    # set a flag used to see if the file could be opened or not to 1 (default)

                    # Try to open File, if file cannot be opened, set flag to -1
                    try:
                        filesend = open(req[1], "r")
                    except Exception as e:
                        print("FIle could not be opened." + str(e))
                        flag = -1
                    # IF the file could be opened
                    if flag != -1:
                        filesize = os.path.getsize('./' + req[1])   # Gets file size in bytes

                        # Create a headed containing information about the file so the server knows how to process it
                        header = "TEXT_" + req[1] + "_" + username + "_" + str(filesize) + "_;"
                        clientSock.send(header.encode())    # Send header to server

                        # This loop ensures that it will only read data from the file while the number of bytes
                        # read is less than or equal to the file size in bytes
                        while count <= filesize:
                            data = filesend.read(1024).encode()     # Read data from file in 1024 byte packets
                            if not data:    # If the data read is null break out of loop
                                break
                            clientSock.send(data)       # Send each packet of data to the server
                            count += len(data)          # increase counter by the length of the data in bytes


                # If the data is not a text file, it is a binary file. Process is same as above
                else:
                    flag = 1
                    try:
                        filesend = open(req[1], "rb")
                    except Exception as e:
                        print("FIle could not be opened." + str(e))
                        flag = -1
                    if flag != -1:
                        filesize = os.path.getsize('./' + req[1])
                        header = "BIN_" + req[1] + "_" + username + "_" + str(filesize) + "_;" # Header starts with BIN
                        clientSock.send(header.encode())
                        while count <= filesize:
                            data = filesend.read(1024)
                            if not data:
                                break
                            clientSock.send(data)
                            count += len(data)
                # Get message from server that the file has sent successfully to server
                print("Sending File")
                message = clientSock.recv(1024)
                print(message.decode())

            # IF the header for the file received from the server is text. Create a text file and read packets into file
            if data.decode().startswith("TEXT"):
                count = 0
                headerList = data.decode().split("_")
                try:
                    clientFile = open(headerList[1], "w")
                except Exception as e:
                    print("Couldnt create file!" + str(e))
                while count < int(headerList[3]):
                    data = clientSock.recv(1024)
                    if data.decode() == "":
                        break
                    clientFile.write(data.decode())
                    clientFile.flush()
                    count += len(data)

                print("File received:")
                print("Name of file:" + headerList[1])
                print("From: " + headerList[2])
                print("Content length:" + str(os.path.getsize('./' + headerList[1])))
                clientFile.close()
                prompt()
            # If the header for thefile recvied from server is BIN, create approprite file and read packets into file
            if data.decode().startswith("BIN"):
                count = 0
                headerList = data.decode().split("_")
                try:
                    clientFile = open(headerList[1], "wb")
                except Exception as e:
                    print("Couldnt create file!" + str(e))
                while count < int(headerList[3]):
                    data = clientSock.recv(1024)
                    if not data:
                        break
                    clientFile.write(data)
                    clientFile.flush()
                    count += len(data)
                print("File received:")
                print("Name of file:" + headerList[1])
                print("From: " + headerList[2])
                print("Content length:" + str(os.path.getsize('./' + headerList[1])))
                prompt()
                clientFile.close()
            # This is when the message came from another user, print and prompt the user to respond
            else:
                sys.stdout.write(data.decode())
                prompt()

        # When the user needs to input a message, format the message with the @username. Send the message off the server
        else:
            message = sys.stdin.readline().rstrip("\n")
            if message.startswith('!'):
                clientSock.send(message.encode())
                prompt()
            else:
                messageSend = "@" + username + ": " + message
                clientSock.send(messageSend.encode())
                prompt()
