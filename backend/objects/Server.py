import logging 
import socket
import json
import concurrent.futures 
import uuid #mac address 
from datetime import datetime #to get the current time 

from utils.server_util import * 


'''

list of issues: 

in client_server_handshake we will have both unencrityed and encripted packets and need to find a way to diffreniate both. 

Need to deciced if when we want to send keep alive packets for online clients 

Need to finish the server_hello_message, decrypt_data, encrypt_data  funcality 

need to finish handel_network_request by adding the client requests 
    add the codes that will be needed for the clients 

need to understand Mac address better 

need to add a goodbye message into server_shutdown

'''


class Server(object):

    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100) # will limit the server to only 100 threads processing data 

    
    def __init__(self, common_name, IP_address, port, multicast_ip):
        self.common_name = common_name
        self.IP_address = IP_address
        self.port = port
        self.multicast_ip = multicast_ip
        self.server_alive = False

    def server_run_call(self):
        self.server_startup(self)
        self.server_on(self)
        self.server_shutdown(self)

    '''
    Tasks: 
        - Log all start up infomation 
        - Check if we have public and private keys and if we need to generate those keys 
        - Needs send multicast message for discovability 
        - connect to the react server 
        - bind the socket conntion and the start listening for connections    
   '''
    def server_startup(self):
        self.logger.info("Server start up begining")

        #check if the public and private keys exists

        #starts to build the network connections
        self.socket_connection.bind(self.IP_address, self.port)
        self.logger.info("Bound socket contion to address: %s and port %d", self.IP_address, self.port) # Need to add checking to see if it fails to bind to the port and address 

        self.socket_connection.listen(5)
        self.server_alive = True

        #connect to the react server 
        self.logger.info("Server starting connection to front-end")


        #send out hello message to multi-cast port 
        self.server_hello_message(self, self.multicast_ip)
        self.logger.info("Server sent discover message")

        self.logger.info("Server start up complted")

    '''
    Tasks: 
        - Set up the script to run so that we can allow multicast connections on the device 
    '''
    def server_hello_message(self, ip_address):

        '''
                # need to send a packet with the code 010 maybe

                
                issue is that for one block of public key encryption we only have 256 bytes which is the whole public key 
                maybe this information does not need to be encypted 
        '''

        #will need to pass this along to the multicast port when requested and send as a response to the multicast ip 
        message = "010" + self.get_mac_address + self.get_public_key + self.common_name


        pass

    def get_mac_address():
        #pulled form chat GPT do not understand this. if you have a better way then let me know 
        mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        return ":".join([mac[e:e+2] for e in range(0, 11, 2)])    

    '''
    Tasks: 
        - create a loop to take all income network connections and send them off to be handeld by a thread 
        - Log each connection 
        - Make sure things are thread safe 

    Key varables: 
        server_alive = this is the varable that can be triggered to shut down the server and stop all incoming connections


    Notes: A client will make one request to the server. If the server needs infomation like the public key from server then it will make it own request to that server 

    '''
    def server_on(self): 
        while(self.server_alive):
            connection, cleint_addresss = self.socket_connection.accept()
            self.logger.info("connection form IP address: %s", str(cleint_addresss)) #string might not be the right data type
            self.thread_pool.submit(self.handel_network_request(connection, cleint_addresss))

    

    '''
    Tasks: 
        - Check and see if the client is allowed to send files to this device 
        - Decrypt the incoming packets 
        - Deal with the request
        - close the connection with the client and treminate thread
        - Log all incoming requests and actions
    '''
    def handel_network_request(self, connection, cleint_addresss):

        work_to_be_done = self.client_server_handshake(self, connection, cleint_addresss)
        incoming_message = ""
        client_handshake_data = ""
        while work_to_be_done:
            while True:
                incoming_message = connection.recv(1024).decode()# Buffer size is 1024 bytes
                if not incoming_message:
                    break

            client_handshake_data = self.decrypt_data(self, incoming_message)

            #find the code and do the request 
            self.logger.info("Client request completed ")

        #complete the request of the client 

        connection.close()

    '''
    Tasks:
        - Complete the handshake 
        - Log the process and result 
    '''
    def client_server_handshake(self, connection, cleint_address):
        handshake_complete = False
        incoming_message = "" 
        client_handshake_data = ""


        while True: # most of these messages should be under 1024 bytes 
            incoming_message = connection.recv(1024).decode()# Buffer size is 1024 bytes
            if not incoming_message:
                break

        #this could be problem as the hello messages will be unencrypted but the handshake messages will be encrypted 
        client_handshake_data = self.decrypt_data(self, incoming_message)
        self.logger.info("Staring Handshake received successfully.")    

        #find if the user is in the json file
        key_length = 256 #need to update with the key lenght of the algo we are using 

        #opens the jsonfile to be updated 
        with open('all-peers.json', 'r+') as file:
            json_file = json.load(file)                
        
        if(client_handshake_data[0:3] == "010"): # this hannles any hello packets from a new client joining the nextwork 
            client_mac_address = client_handshake_data[3:6]
            client_public_key = client_handshake_data[6:key_length+6]
            client_common_name = client_handshake_data[key_length+6:]

            if client_public_key in json_file:

                #update the IP address of the client 
                if(cleint_address != json_file[client_public_key]["most_recent_ip"]):
                            json_file[client_public_key]["most_recent_ip"] = cleint_address
                
                json_file[client_public_key]["online"] = True

                
            else:
                new_data = {
                    client_public_key:{
                        "online": True,
                        "session_start_time": datetime.now().time(),
                        "allowed_to_receive": -1,
                        "most_recent_ip": cleint_address,
                        "common_name": client_common_name,
                        "mac_address": client_mac_address,
                        "have_shared_before": 0,
                        "currently_storing_with": 0,
                        "total_gb_storing_with": 0,
                        "currently_storing_for": 0,
                        "total_gb_storing_for": 0,
                        "files_stored_with": []
                    }
                }

                json_file.update(new_data)
                self.logger.info("Client %s just joined the list of know users", client_public_key)


            self.logger.info("Client %s just joined the network", client_public_key)


            self.server_hello_message(self, cleint_address)
        else: # this starts the handshake process for a existing connection on the nextwork 
            client_public_key = client_handshake_data[0:key_length]
            if client_public_key in json_file:
                self.logger.info("Client public key is in data base") 

                #if the user is in the json file then it will decide if it can approved, blocked or waiting for approvle. 
                if client_public_key in json_file:
                    if(json_file[client_public_key]["allowed_to_receive"] == 1):
                        self.logger.info("Client is allowed to send to this device")

                        if(cleint_address != json_file[client_public_key]["most_recent_ip"]):
                            json_file[client_public_key]["most_recent_ip"] = cleint_address

                        #start the handshake process to confirm who they are 
                        passcode = self.generate_passcode(self)
                        outgoing_message = self.encrypt_data(self, client_public_key, passcode)
                        connection.send(outgoing_message.encode())
                        incoming_message = connection.recv(1024).decode()
                        client_handshake_data = self.decrypt_data(self, incoming_message)
                        if(passcode == client_handshake_data):
                            handshake_complete = True
                            self.logger.info("Client passed the handshake")
                        else:
                            self.logger.info("Client failed the handshake")

                    elif (json_file[client_public_key]["allowed_to_receive"] == -1):
                        self.logger.info("Client is waiting approvel to send to this device")
                        # send message stating they they are in a waiting state
                        message = "waiting"
                        outgoing_message = self.encrypt_data(self, client_public_key, message)
                        connection.send(outgoing_message.encode())
                        self.logger.info("Client is in a waiting state")
                    else:
                        self.logger.info("Client is not allowed to send to this device")
                        # send a message stating they are blocked from this device 
            else:
                self.logger.info("Client public key is not in the data base")   

        return handshake_complete
    
    '''
    This function will be used to decrypt all data sent to the device 
    '''
    def decrypt_data(self, message):
        data = message 
        return "data" 
    
    '''
    This function will be used to encrypt all data sent to the device 
    '''
    def encrypt_data(self, client_public_key, data):
        message = data 

        return message 

    '''
    Tasks: 
        - close all of the threads on the server 
        - close connection to the react server 
        - Log all of data 
    '''
    def server_shutdown(self):
        self.logger.info("Server shutdown started")

        self.thread_pool.shutdown(wait=True)
        
        self.logger.info("Server shutdown completed")