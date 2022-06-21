import os
from socket import *
import time
import hashlib
import BadNet5 as badnet
import select

serverName = '10.7.85.22'
serverPort = 12000

clientSocket = socket(AF_INET, SOCK_DGRAM)  # client socket of unreliable data transfer
object_badNet = badnet.BadNet()       # object of imported BadNet class

# Class for modifying the UDT to RDT
class rdt:
    # initializing the variables
    rtt = 0.0001
    timeoutinterval = 0.0002
    Devrtt = 0
    seq_no = 1
    samplertt = 0
    counter = 0
    packetbuffer = []

    @staticmethod
    def rdt_send(csocket, message, serverName, serverPort):
        seq_no = str(rdt.seq_no)  # Convert the sequence number to string
        zeros_to_add = 32 - len(seq_no)
        while zeros_to_add > 0:        # Extend the sequence number to 32 bits
            seq_no = "0" + seq_no
            zeros_to_add = zeros_to_add - 1

        packetwithoutchecksum = seq_no + message    # packet containing sequence number and message
        check = hashlib.md5(packetwithoutchecksum.encode())     # returns hash value for bytes
        checksum = check.hexdigest()        # returns the data of checksum in hexadecimal format
        packet = checksum + packetwithoutchecksum       # packet containing sequence number, message and checksum
        # if file is not ended, buffer file into the buffer list
        if (message != "end"):
            rdt.packetbuffer.append(packet)
            rdt.seq_no = rdt.seq_no + 1
            return

        # if file is fully read, first make connection and then send packets to the receiver
        # Receiver will buffer in its own buffer list
        else:
            connection = "false"
            connection = connection.encode()
            while (connection.decode()) != "True":
                buffer_size = len(rdt.packetbuffer)
                print("Buffer Size: ",buffer_size)
                # Making connection packet
                buffer_packet_without_checksum = (
                                                "00000000000000000000000000000000") + (str(buffer_size))
                buffer_check = hashlib.md5(
                    buffer_packet_without_checksum.encode())
                buffer_checksum = buffer_check.hexdigest()
                buffer_packet = buffer_checksum + buffer_packet_without_checksum
                object_badNet.transmit(clientSocket, buffer_packet.encode(),
                             serverName, serverPort)
                clientSocket.setblocking(0)
                ready = select.select(
                    [clientSocket], [], [], rdt.timeoutinterval)
                if (ready[0]):
                    connection, serverAddress = clientSocket.recvfrom(1024)
            print("Connection established")
            size = len(rdt.packetbuffer)
            # loop to check if the acknowledgement of all the packets has been received
            while size > 0:
                print(
                    "The size=--------------------------------------------------"
                    "------------------------",
                    size)
                pack = 0
                # Traversing the buffer list of sender and send the packets in a pipeline fashion
                while pack < len(rdt.packetbuffer):
                    # check if ack is already received
                    if (rdt.packetbuffer[pack] == None):
                        pack = pack + 1
                        continue
                    # if ack is not already received then send the packet and receive the ack
                    else:
                        data = rdt.packetbuffer[pack]
                        start_time = time.time()
                        object_badNet.transmit(clientSocket, data.encode(),
                                     serverName, serverPort)
                        clientSocket.setblocking(0)
                        ready = select.select(
                            [clientSocket], [], [], rdt.timeoutinterval)
                        if (ready[0]):
                            ackpacket, serverAddress = clientSocket.recvfrom(
                                1024)
                            end_time = time.time()
                            rdt.samplertt = end_time - start_time
                            rdt.rtt = (((1 - 0.125) * rdt.rtt) +
                                       (0.125 * (rdt.samplertt)))
                            rdt.Devrtt = (((1 - 0.25) * rdt.Devrtt) +
                                          (0.25 * abs(rdt.samplertt - rdt.rtt)))
                            rdt.timeoutinterval = rdt.rtt + 4 * rdt.Devrtt
                            ackpacket = ackpacket.decode()
                            ackchecsum = ackpacket[0:32]
                            ackseq = ackpacket[32:]
                            ackcheck = hashlib.md5(ackseq.encode())
                            ackchecsum1 = ackcheck.hexdigest()
                            # Condition that check the ack is correct
                            # if error occurred in the ack then it will be discarded
                            if (ackchecsum == ackchecsum1):
                                print(
                                    "Index of the list ...................................................",
                                    int(ackseq))
                                if (rdt.packetbuffer[int(ackseq) - 1] != None):
                                    rdt.packetbuffer[int(ackseq) - 1] = None
                                    size = size - 1
                                    if (size == 0):
                                        break
                        pack = pack + 1
                        continue

            # Preparing packet which will contain message that the file has been completely transfered
            message = "end"
            sequence = "00000000000000000000000000000000"
            packetwithoutchecksum = sequence + message
            check = hashlib.md5(packetwithoutchecksum.encode())
            checksum = check.hexdigest()
            packet = checksum + packetwithoutchecksum
            object_badNet.transmit(clientSocket, packet.encode(),
                         serverName, serverPort)


# Getting file details.
file_name = input("Enter the file Name:")

# Opening file and sending data.
with open(file_name, "r") as file:
    rdt_transfer = rdt()        # Make object of rdt class
    # Start the timer for the file transfer
    start_time = time.time()
    while True:
        data = file.read(1024)
        if not (data):
            print("File has been read successfully!!")
            rdt_transfer.rdt_send(clientSocket, "end",
                               serverName, serverPort)
            break
        else:
            rdt.rdt_send(clientSocket, data,
                         serverName, serverPort)
    # End the timer after file has been transferred
    end_time = time.time()

print("File Transfer Completed!!Total time: ", end_time - start_time)
# Closing the file.
file.close()
# Closing the socket.
clientSocket.close()
