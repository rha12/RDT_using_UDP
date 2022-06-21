# importing modules
import os
from socket import *
import time
import hashlib
import select
import BadNet5 as badnet
serverPort = 12000
serverSocket = socket(AF_INET, SOCK_DGRAM)  # server socket of unreliable data transfer
serverSocket.bind(('10.7.85.22', serverPort))
object_badNet = badnet.BadNet()     # object of imported BadNet class

# Class for modifying the UDT to RDT
class rdt:
    bufferlist = []

    @staticmethod
    def rdt_rcv():
        start_time = time.time()
        # receiving packet from the client
        while True:
            packet, clientAddress = serverSocket.recvfrom(2048)
            packet = packet.decode()
            checksum = packet[0:32]
            packetwithoutchecksum = packet[32:]
            check1 = hashlib.md5(packetwithoutchecksum.encode())
            checksum1 = check1.hexdigest()
            # Check---> if packet is correct, then accept; otherwise discard the packet
            if(checksum == checksum1):
                seqno_received = packet[32: 64]
                message = packet[64:]
                # Check if file has been completed
                if (message == "end"):
                    # write data into the file from buffer list.
                    object_badNet.transmit(serverSocket, ("end").encode(),
                                 clientAddress[0], clientAddress[1])
                    # Creating a new file or removing its previous content.
                    file = open("./rec/receivedfile.txt", "w")
                    file.close()
                    # Opening and reading file.
                    with open("./rec/receivedfile.txt", "a") as file:
                        # Start the timer for file writing.
                        # Loop to write data from buffer to the file
                        pack = 0
                        while pack < (len(rdt.bufferlist)):
                            data = rdt.bufferlist[pack]
                            file.write(data)
                            pack = pack+1
                        # End the timer after the file has been written
                        end_time = time.time()
                    print("File transfer Complete!! Total time: ",
                          end_time - start_time)
                    return
                # Check if the received packet is the first one (connection packet)
                # containing the information of buffer size
                elif(int(seqno_received) == 0):
                    # make buffer list and ack connection packet to the sender
                    rdt.bufferlist = [None]*(int(message))
                    object_badNet.transmit(serverSocket, ("True").encode(),
                                 clientAddress[0], clientAddress[1])
                    print("Buffer list created with size: ", int(message))
                else:
                    # receive packet, store it in the buffer list and ack that packet to the sender
                    rdt.bufferlist[int(seqno_received)-1] = message
                    ackcheck = hashlib.md5(seqno_received.encode())
                    ackchecksum = ackcheck.hexdigest()
                    ackpacket = ackchecksum+seqno_received
                    object_badNet.transmit(serverSocket, ackpacket.encode(),
                                 clientAddress[0], clientAddress[1])
            else:
                continue


print("The server is ready to receive........")
rdt_transfer = rdt()
rdt_transfer.rdt_rcv()
# Closing the socket.
serverSocket.close()
