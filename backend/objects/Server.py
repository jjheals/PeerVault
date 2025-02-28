import logging 
import socket
import json
import concurrent.futures 
import uuid #mac address 
from datetime import datetime #to get the current time 
import cryptography as c
from cryptography.hazmat.primitives import serialization, hashes, padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

from utils.server_util import * 


'''

list of issues: 

in client_server_handshake we will have both unencrityed and encripted packets and need to find a way to diffreniate both. 

Need to deciced if when we want to send keep alive packets for online clients 

Need to finish the server_hello_message, functionality 

need to finish handle_network_request by adding the client requests 
    add the codes that will be needed for the clients 

need to understand Mac address better 

need to add a goodbye message into server_shutdown

'''


class Server(object):

    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100) # will limit the server to only 100 threads processing data 

    
    DISC_CODE:str = "000"
    IDC_CODE:str = "001"
    SEND_REQ_CODE:str = "101"
    STORE_REQ_CODE:str = "102"
    DEL_FILE_CODE:str = "103"
    UPD_FILE_CODE:str = "104" 


    def __init__(self, common_name, IP_address, port, multicast_ip, key_length):
        self.common_name = common_name
        self.IP_address = IP_address
        self.port = port
        self.multicast_ip = multicast_ip
        self.server_alive = False
        self.key_length = key_length

        # Call initialization funcs
        self.server_startup(self)
        self.server_on(self)
        self.server_shutdown(self)
        

    
# ____________________________________--encryption methods--___________________________________________
    
    def save_keys(private_key, public_key):
        
        with open("private.pem", "wb") as pem:
            pem.write(private_key)

        with open("public.pem", "wb") as pempub:
            pempub.write(public_key)

    def generate_keys(password):
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096)

        
        private_key = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            encryption_algorithm= serialization.BestAvailableEncryption(password)
        )

        public_key = key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # generates a random 256 bit key... 
        key = os.urandom(32)
        iv = os.urandom(16)
        AES_doer = Cipher(algorithms.AES(key), modes.CBC(iv))

        save_keys(private_key, public_key)
        
        return AES_doer

    def get_private_key(password):
        try:
            with open("private.pem", "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    data=key_file.read(),
                    password=password, 
                    backend=default_backend
                )
            return private_key
        
        except Exception as e:
            print(f"Error opening PEM file: {e}")
            return None
        
    def get_public_key():
        try:
            with open("public.pem", "rb") as key_file:
                public_key = serialization.load_pem_public_key(
                    data=key_file.read(),
                    backend=default_backend
                )
            return public_key
        
        except Exception as e:
            print(f"Error opening PEM file: {e}")
            return None

    def parse_data(file):
        with open(file, "rb") as data:
            parsed_data = data.read()  

        return parsed_data

    def RSA_encrypt(data, key):
        cipher = key.encrypt(data,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
        return cipher

    def RSA_decrypt(data, key):
        message = key.decrypt(data,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None  
                    )
                )

        return message

    def AES_encrypt(data, doer):
        padder = c.hazmat.primitives.padding.PKCS7(128).padder()
        padded_data = padder.update(data)
        padded_data += padder.finalize()

        encryptor = doer.encryptor()
        cipher = encryptor.update(padded_data) + encryptor.finalize()
        return cipher

    def AES_decrypt(data, doer):
        decryptor = doer.decryptor()
        text = decryptor.update(data) + decryptor.finalize() 

        unpadder = c.hazmat.primitives.padding.PKCS7(128).unpadder()
        unpadded_data = unpadder.update(text)
        unpadded_data += unpadder.finalize()
        return  unpadded_data

    # TODO -- this is untested...
    def hashMessage(data):
        digest = hashes.Hash(hashes.SHA256())
        digest.update(data)
        digest.finalize()
        return digest

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
        self.discover_message(self, self.multicast_ip)
        self.logger.info("Server sent discover message")

        self.logger.info("Server start up completed")


    def discover_message(self, ip_address):

        '''
        Send a discover message to the ip_address

        When handshake is started it might try and send a message back to this method which would have closed already ... Will need to do testing
        '''

        #will need to pass this along to the multicast port when requested and send as a response to the multicast ip 
        try:

            message = Server.DISC_CODE + self.get_public_key() + self.get_mac_address() + self.common_name
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(ip_address)
            s.sendall(message.encode())
            self.logger.info("Sent discover message to IP: %s", str(ip_address))

        except socket.error as e:
            self.logger.info("Failed to send discover message to IP: %s", str(ip_address))           

        finally:
            # Close the socket
            s.close()


    def get_mac_address():
        """Returns the MAC address of the current machine."""
        mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        return ":".join([mac[e:e+2] for e in range(0, 11, 2)])    


    def server_on(self): 
        """Turns on the server and starts listening for requests. Breaks the incoming requests into threads to be handled separately.
                
        Tasks: 
            - create a loop to take all income network connections and send them off to be handled by a thread 
            - Log each connection 
            - Make sure things are thread safe 

        Notes: A client will make one request to the server. If the server needs infomation like the public key from server then it will make it own request to that server 
        """
        while(self.server_alive):
            connection, client_address = self.socket_connection.accept()
            self.logger.info("connection form IP address: %s", str(client_address)) 
            self.thread_pool.submit(self.handle_network_request(connection, client_address))

    
    def handle_network_request(self, connection, client_address):
        """Takes in a connection and client address and completes the identity check handshake, then calls the appropriate method to handle
        the client's request. 

        Tasks: 
            - Check and see if the client is allowed to send files to this device 
            - Decrypt the incoming packets 
            - Deal with the request
            - close the connection with the client and treminate thread
            - Log all incoming requests and actions
        """

        # Get the message 
        incoming_message:str = ""

        while True:
            incoming_message = connection.recv(1024).decode()# Buffer size is 1024 bytes
            if not incoming_message:
                break
        
        # TODO: Get the message code from the incoming_message
        message_code:str = incoming_message[0:3]
        client_public_key = incoming_message[3:3+self.key_length]
        message = incoming_message[3+self.key_length:]

        # Handle the message code appropriately
        match message_code: 
            
            # Handle discovery code
            case Server.DISC_CODE:

                # Do identity check
                id_check_result:bool = self.initiate_identity_check(connection, client_public_key, client_address, self.DISC_CODE)  

                # If ID check pass, handle the discovery request
                if id_check_result: 
                    self.handle_discovery_code(connection, client_public_key, incoming_message, client_address)
                # If ID check failed, do not respond
                else: 
                    pass
            
            # Handle identity check code
            case Server.IDC_CODE: 
                # Complete incoming req for an identity check
                self.responde_identity_check(self, connection, client_address, message) 
            
            # Handle send request code
            case Server.SEND_REQ_CODE: 

                # Do identity check
                id_check_result:bool = self.initiate_identity_check(connection, client_address)  

                # If ID check pass, handle the discovery request
                if id_check_result: self.handle_send_request( '''SOME ARGUMENTS ''' )
                
                # If ID check failed, do not respond
                else: pass
            
            # Handle store request code
            case Server.STORE_REQ_CODE: 
                # Do identity check
                id_check_result:bool = self.initiate_identity_check(connection, client_address)  

                # If ID check pass, handle the discovery request
                if id_check_result: self.handle_store_request(
                    connection,
                    remote_peer_pub_key
                )
                
                # If ID check failed, do not respond
                else: pass
            
            # Handle delete file code
            case Server.DEL_FILE_CODE: 
                # Do handshake
                # Delete the file from the system
                pass
            
            # Handle update file code
            case Server.UPD_FILE_CODE: 
                # Do handshake
                # Update the file 
                pass
            
            # Handle other (invalid) code
            case _: 
                # Do not respond 
                pass

        connection.close()


    def initiate_identity_check(self, connection, client_public_key, client_address, code) -> bool:
        """Complete an identity check handshake with the given connection and client address.
        
        Tasks:
            - Complete the handshake 
            - Log the process and result 

        Returns: 
            (bool) True if the remote peer passes the identity check, False otherwise.
        """

        client_handshake_data = ""           

        # Start the identity check handshake 
        self.logger.info("Starting Handshake with client (%s)", client_address) 
        # TODO --> change password mechanism
        password = "CHANGEME"  
        AESdoer = self.generate_keys(password)  
        # TODO --> what is the message?
        outgoing_message:str = str(self.IDC_Code + self.get_public_key() + self.AES_encrypt(data, AESdoer))    # Encrypt the outgoing passcode
        connection.send(outgoing_message.encode())                                                                                  # Send the encrypted passcode
        ciphertext_message:str = connection.recv(1024).decode()                                                                     # Wait for an incoming response
                                            # ^ we should change the above to the expected size of the packet we are going to get
        client_handshake_data = self.AES_decrypt( ciphertext_message, AESdoer)                                       # Decrypt the incoming response

        # Check that the client supplied the correct passcode
        if(passcode == client_handshake_data):
            # Client passed handshake
            self.logger.info("Client (%s) returned the correct passcode", str(client_address))                          # Log result

            # Open the all peers json to read the incoming data 
            with open('all-peers.json', 'r') as file:
                all_peer_data = json.load(file)  
            
            '''
            Checks if we have the public key in the "database" (checking to see if we are looking at an old user)

            if not in the database going to assume that it is a new user 
            
            '''
            if client_public_key in all_peer_data:
                if(all_peer_data[client_public_key]["allowed_to_receive"] == 1):   
                    self.logger.info("Client (%s) is allowed to send to this device", str(client_address))              # Log result
                    # TODO --> what is the message?
                    outgoing_message:str = str(self.IDC_Code + self.get_public_key() + self.AES_encrypt(data, AESdoer))    # Encrypt the outgoing passcode
                    connection.send(outgoing_message.encode())
                    return True                                                                                         # Return that peer passed       
    
                elif (all_peer_data[client_public_key]["allowed_to_receive"] == -1):
                    # TODO: send notif to react app that we are waiting for approval or disapproval for the peer to send us something
                    # DO SOMETHING ...

                    # Send message back to peer stating they they are in a waiting state
                    outgoing_message:str = str(self.IDC_Code + self.get_public_key() + self.AES_encrypt(data, AESdoer))    # Encrypt the outgoing passcode
                    connection.send(outgoing_message.encode())                                                          # Send message
                    self.logger.info("Client (%s) is waiting approvel to send to this device", str(client_address))     # Log

                # Peer is not allowed to send us a message
                else:
                    self.logger.info("Client (%s) is not approved to send to this device", str(client_address))         # Log

            elif (code == self.DISC_CODE): 
                # TODO: send notif to react app that we are waiting for approval or disapproval for the peer to send us something
                # DO SOMETHING ...

                # Send message back to peer stating they they are in a waiting state
                outgoing_message = self.AES_encrypt(data, AESdoer)                                # Encrypt message
                connection.send(outgoing_message.encode())                                                              # Send message
                self.logger.info("New client (%s) is sending discovery message", str(client_address))                   # Log
                return True                                                                                             # Return that peer passed       
            ''' Do not like how we have mutiple diffrent return statements here'''

        # Client failed handshake 
        self.logger.info("Client (%s) failed the handshake", str(client_address))     # Log result
        outgoing_message:str = str(self.IDC_Code + self.get_public_key() + self.AES_encrypt(data, AESdoer))    # Encrypt the outgoing passcode
        connection.send(outgoing_message.encode())
        
        return False  


    def responde_identity_check(self, connection, client_address, client_public_key, ciphertext_message, AESdoer) -> bool:

        self.logger.info("Reviced passcode from client (%s)", str(client_address))                   # Log
        passcode_recived = self.decrypt_data(self.get_private_key, ciphertext_message)
        # TODO --> what is the message?
        outgoing_message:str = str(self.get_public_key() + self.AES_encrypt(data, AESdoer))
        connection.send(outgoing_message.encode())                                                                                 # Send the encrypted passcode

        check_passed:str = connection.recv(1024).decode()                                                                     # Wait for an incoming response
        if(check_passed == "passed"):
            self.logger.info("Passed identity check with client (%s)", str(client_address))                   # Log
            return True
        else:
            '''
            send a message to the user that they are not approved to send to this user
            '''
            self.logger.info("Failed identity check with client (%s)", str(client_address))                   # Log
            return False

    def handle_discovery_code(self, connection, client_public_key:str, client_handshake_data:str, client_address:str) -> dict: 
        """Handles a discovery request.
        
        Tasks: 
            - Check JSON and update if necessary
            - Send message back to remote peer via the given connection

        Returns: 
            Dictionary like: 
                { 
                    "status": "success",
                    "message": "Remote peer identified successfully."
                }
        """
        # Open the all peers json to read and write the incoming data 
        with open('all-peers.json', 'r+') as file:
            all_peer_data = json.load(file) 

        client_public_key   = client_handshake_data[3:self.key_length+3]
        client_mac_address  = client_handshake_data[self.key_length+3:self.key_length+9]
        client_common_name  = client_handshake_data[self.key_length+9:]            

        # Check if we've seen this pub key before
        if client_public_key in all_peer_data:

            # If we have seen this user, update the IP of the user in the json file and set their status to "online"
            if(client_address != all_peer_data[client_public_key]["most_recent_ip"]):
                all_peer_data[client_public_key]["most_recent_ip"] = client_address
                self.logger.info("Client %s changed there IP", client_public_key)

            all_peer_data[client_public_key]["session_start_time"] = datetime.now().time()
            all_peer_data[client_public_key]["online"] = True

        # If we haven't seen this user before, create a new entry for this user
        else:
            new_data = {
                client_public_key:{
                    "online": True,
                    "session_start_time": datetime.now().time(),
                    "allowed_to_receive": -1,
                    "most_recent_ip": client_address,
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

            # Add the new entry to the json data and update the file
            all_peer_data[client_public_key] = new_data
            # Log update
            self.logger.info("Client %s just joined the list of know users", client_public_key)

        # Log that a new client was found
        self.logger.info("Client %s just joined the network", client_public_key)

        # Send a message back to the client 
        self.discover_message(self, client_address)
    

    def handle_send_request(self, new_data:dict) -> None: 
        """Handles a request from a remote peer to send a file to this peer.
        
        Tasks: 
            - Check that the remote peer is allowed to send to this peer
                - Send an "allowed" message to the remote peer (if allowed)
                    - Send a "denied" message to the remote peer (if not allowed)
                - If allowed, handle the next response from the remote peer with the file data 
                    - Store the file appropriately
                    - Update JSON with new metadata
                    - Show the file to the react app/make available to react app ?? (not sure how this will happen yet)
        """
        raise NotImplementedError


    def handle_store_request(self, connection, remote_peer_pub_key:str) -> None: 
        """Handles a request from a remote peer to store a file on this peer.
        
            Tasks: 
                - Check that the remote peer is allowed to store with this peer
                    - Send an "allowed" message to the remote peer (if allowed)
                    - Send a "denied" message to the remote peer (if not allowed)
                - If allowed, handle the next response from the remote peer with the file data 
                    - Store the file appropriately
                    - Update JSON with new metadata
        """

        raise NotImplementedError



    def server_shutdown(self):
        """Shuts down the server and closes all sockets.
        
        Tasks: 
            - close all of the threads on the server 
            - close connection to the react server 
            - Log all of data 
        """

        self.logger.info("Server shutdown started")

        self.thread_pool.shutdown(wait=True)
        
        self.logger.info("Server shutdown completed")
