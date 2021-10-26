# CS 3357 Assignment 1 Matthew Cheverie 251098050
# This file runs the chat client for the user. It uses select to handle multiplexing. Sys for dealing with the terminal.
# uses urlparse to parse through the command line arguments. Uses signal to handle control C inputs
from socket import *
import select
import sys
from urllib.parse import urlparse
import signal


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
            data = sock.recv(4096)

            # If no data is recived and error occurred and the client is disconnected
            if not data:
                print('Disconnected!!')
                clientSock.close()
                sys.exit()

            # If a server disconnect message is received, shut down this client and exit the system
            elif data.decode() == "DISCONNECT CHAT/1.0":
                print("Server is shutting down! All clients will be disconnected")
                clientSock.close()
                sys.exit(0)

            # This is when the message came from another user, print and prompt the user to respond
            else:
                sys.stdout.write(data.decode())
                prompt()
        # When the user needs to input a message, format the message with the @username. Send the message off the server
        else:
            message = sys.stdin.readline()
            messageSend = "@" + username + ": " + message
            clientSock.send(messageSend.encode())
            prompt()
