import logging 
import socket
import struct
import json
import os
import concurrent.futures 

from datetime import datetime #to get the current time 
import pandas as pd 

from utils import strip_pem_headers, generate_random_passcode, encrypt_message, decrypt_message, now, update_peer_info


class Server(object):

    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100) # will limit the server to only 100 threads processing data 

    common_name:str             # The common name for this client
    iface:str                   # The interface (address) the server is running on
    pub_key_pem:str             # This client's public key (with PEM headers)
    priv_key_pem:str            # This client's private key (with PEM headers)
    data_dir_path:str           # Path to the directory containing the CSVs (all-peers.csv, etc...)
    
    # STATIC ATTRIBUTES
    DISC_CODE:str = "000"       # Code for a discovery message
    INIT_IDC_CODE:str = "011"   # Code for initiating an identity check
    RESP_IDC_CODE:str = "012"   # Code for responding to an identity check
    SHARE_REQ_CODE:str = "101"   # Code for requesting to share a file
    STORE_REQ_CODE:str = "102"  # Code for requesting to store a file
    DEL_FILE_CODE:str = "103"   # Code for requesting to delete a file
    UPD_FILE_CODE:str = "104"   # Code for requesting to update a stored file

    BUFF:int = 2048             # Buffer for requests

    def __init__(self, pub_key_pem:str, priv_key_pem:str, common_name:str, iface:str, data_dir_path:str):
        self.pub_key_pem = pub_key_pem
        self.priv_key_pem = priv_key_pem
        self.common_name = common_name
        self.iface = iface
        self.server_alive = False
        self.data_dir_path = data_dir_path
        
        print('\033[92mServer init complete.\033[0m')
        # Call initialization funcs
        '''
        if self.server_startup():
            self.server_on()
            self.server_shutdown()
        else:
            self.logger.error("Server startup failed. Initialization aborted.")
        '''     

    # ---- Methods related to SERVER INITIALIZATION and SHUTDOWN ---- #
    def server_startup(self) -> bool:
        """ Initializes the server, checks for necessary keys, binds the socket, and starts listening for connections."""
        
        self.logger.info("Server startup beginning")

        # Check if the public and private keys exist and are accessible
        if not self.check_keys():
            self.logger.info("Generating new keys")
            self.generate_keys(self)

        # Start to build the network connections
        try:
            self.socket_connection.bind((self.IP_address, self.port))
            self.logger.info("Bound socket connection to address: %s and port %d", self.IP_address, self.port)
        except Exception as e:
            self.logger.error("Failed to bind socket connection: %s", e)
            return False

        try:
            self.socket_connection.listen(5)
            self.server_alive = True
            self.logger.info("Server is now listening for connections")
        except Exception as e:
            self.logger.error("An error occurred while starting to listen for connections: %s", e)
            return False

        # Connect to the React server
        try:
            self.logger.info("Server starting connection to front-end")
            # Assuming there's a method to connect to the front-end
            self.connect_to_frontend()
        except Exception as e:
            self.logger.error("Failed to connect to front-end: %s", e)
            return False

        # Send out hello message to multicast port
        try:
            self.discover_message(self, self.multicast_ip)
            self.logger.info("Server sent discover message")
        except Exception as e:
            self.logger.error("Failed to send discover message: %s", e)
            return False

        self.logger.info("Server startup completed")
        return True


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


    # ---- Server LISTENER UTILS ---- #
    def listen(self) -> None: 
        """Turns on the server and starts listening for requests. Breaks the incoming requests into threads to be handled separately.
                
        Tasks: 
            - create a loop to take all income network connections and send them off to be handled by a thread 
            - Log each connection 
            - Make sure things are thread safe 

        Notes: A client will make one request to the server. If the server needs infomation like the public key from server then it will make it own request to that server 
        """
        while(self.server_alive):

           # Accept the incoming connection
            cxn, addr = self.socket_connection.accept()

            # Log
            self.logger.info("connection form IP address: %s", str(addr[0])) 

            # Pass connection to handle network req func in a new thread        
            self.thread_pool.submit(self.handle_network_request(
                cxn, 
                addr
            ))


    def mcast_listen(self, mcast_iface, mcast_port, mcast_group) -> None: 
        
        # Create the socket
        sock = socket.socket(
            socket.AF_INET,         # Specify IPv4
            socket.SOCK_DGRAM,      # UDP socket
            socket.IPPROTO_UDP      # UDP protocol 
        )

        # Enable address reuse 
        sock.setsockopt(
            socket.SOL_SOCKET,      # Apply to the socket 
            socket.SO_REUSEADDR,    # Allow multiple sockets to bind to the same port
            1                       # 1 = enable, 0 = disable
        )

        # Bind the socket to the correct interface and port
        sock.bind((mcast_iface, mcast_port))

        # Pack group and interface together 
        mreq = struct.pack( 
            "4s4s",                         # Pack format 
            socket.inet_aton(mcast_group),    # Convert mcast group addr to binary
            socket.inet_aton(mcast_iface)         # Convert local interface/addr to binary
        )

        sock.setsockopt(
            socket.IPPROTO_IP,          # Modifying an IP-level setting 
            socket.IP_ADD_MEMBERSHIP,   # Join multicast group
            mreq                        # Group & local interface pack
        )

        # Listen for incoming messages
        print("[Multicast Listener] Listening for peer announcements...")

        while True:
            data, addr = sock.recvfrom(1024)  # Receive message
            peer_info = data.decode()

            print(f"[Listener] New peer discovered: {peer_info}")


    def handle_network_request(self, connection:socket.socket, addr:tuple[str, int], data:dict, print_info:bool=False) -> None: 
        """Takes in an incoming connection, the addr info (in the format (ip, port)), checks the requirements of the message, initiates an identity check if required,
        and passes the connection off to the appropriate function.

        Args:
            connection (socket.socket): incomming connection to handle.
            print_info (bool, optional): Specify whether to print info statements to the terminal. Defaults to False.
        
        NOTE: recommended to call TcpListener.listen() in a loop, e.g.: 
        
            while True: 
                tcp_listener.listen()
        """
        
        # Info print about the incoming connection
        if print_info:
            print(f'\033[0m[{now()}] \033[92mIncoming connection\033[0m')
            print(f'\n\t\033[0mPeer (IP, PORT): {addr}')

        # Read the incoming data
        data = connection.recv(self.BUFF)

        # Extract the JSON and conver to a python dict
        message_json:dict = json.loads(data.decode())

        # Info print
        if print_info: print(f'\t\033[0mExtracted message JSON: {message_json}')

        # Check for the required keys in the body
        code:int = message_json.get('code', None)
        peer_pub_key_pem:str = message_json.get('public_key_pem', None)
        peer_common_name:str = message_json.get('common_name', None)
        peer_mac_last_four:str = message_json.get('mac_last_four', None)
        
        # If no code or pub key, ignore the message and close the cxn
        if not all([code, peer_pub_key_pem, peer_common_name, peer_mac_last_four]): 
            print('\n\t\033[91mERROR: \033[0mmessage does not contain one of [code, public_key_pem, common_name, mac_last_four] - ignoring message.\033[0m')
            connection.close()
            return      
        
        # If all required attributes are present, handle the request code appropriately
        match code: 
            
            # Handle discovery code (new peer joined the network)
            case Server.DISC_CODE:

                # Do identity check
                id_check_result:bool = self.initiate_identity_check(
                    connection, 
                    peer_pub_key_pem, 
                    addr[0]
                )  
 
                # If ID check pass, update the peer's info
                if id_check_result: 
                    update_peer_info(
                        strip_pem_headers(peer_pub_key_pem), 
                        os.path.join(self.data_dir_path, 'all-peers.csv'),
                        {
                            'peer_ip': addr[0],
                            'peer_common_name': peer_common_name,
                            'peer_mac_last_four': peer_mac_last_four,
                            'peer_status': True
                        }
                    )
                    
                # If ID check failed, do not respond and do nothing else 
                else: pass
            
            # Handle identity check code (peer wants us to complete an identity check)
            case Server.INIT_IDC_CODE: 
                self.respond_identity_check(
                    connection, 
                    addr[0], 
                    peer_pub_key_pem, 
                    data
                )
            
            # Handle share request code (peer wants to share a file with us)
            case Server.SHARE_REQ_CODE: 

                # Do identity check
                id_check_result:bool = self.initiate_identity_check(
                    connection, 
                    peer_pub_key_pem, 
                    addr[0]
                )  

                # If ID check pass, handle the discovery request
                if id_check_result: 
                    self.handle_share_request(
                        # TODO: ADD PARAMS 
                        # ...
                    )
                    
                # If ID check failed, do not respond
                else: pass
            
            # Handle store request code (peer wants to store a file with us)
            case Server.STORE_REQ_CODE: 
                
                # Do identity check
                id_check_result:bool = self.initiate_identity_check(
                    connection, 
                    peer_pub_key_pem, 
                    addr[0]
                )  

                # If ID check pass, handle the discovery request
                if id_check_result: 
                    self.handle_store_request(
                        # TODO: ADD PARAMS 
                        # ...
                    )
                
                # If ID check failed, do not respond
                else: pass
            
            # Handle delete file code (peer wants to delete a file we are storing for them)
            case Server.DEL_FILE_CODE: 
                
                # Do identity check
                id_check_result:bool = self.initiate_identity_check(
                    connection, 
                    peer_pub_key_pem, 
                    addr[0]
                )  

                # Delete the file from the system
                if id_check_result: 
                    self.handle_delete_request(
                        # TODO: ADD PARAMS 
                        # ...
                    )
                
                # If ID check failed, do not respond
                else: pass

            # Handle update file code (peer wants to update a file we are storing for them)
            case Server.UPD_FILE_CODE: 
                
                # Do identity check
                id_check_result:bool = self.initiate_identity_check(
                    connection, 
                    peer_pub_key_pem, 
                    addr[0]
                )  
                
                # Update the file 
                if id_check_result: self.handle_update_request(
                    # TODO: ADD PARAMS 
                    # ...
                )
                
                # If ID check failed, do not respond
                else: pass

            # Handle other code (invalid)
            case _: 
                # Do not respond 
                pass
        
        # Close the connection
        connection.close()


    # ---- Methods that HANDLE INCOMING REQUESTS ---- #    
    # NOTE: the reverse methods of "Methods related to SENDING INFO TO OTHER PEERS"

    def respond_identity_check(self, connection:socket.socket, client_address:str, client_public_key:str, ciphertext_message:dict) -> bool:
        """Takes in a connection and other info and responds to the incoming identity check."""
        
        # Load the incoming message JSON
        incoming_message_json:dict = json.loads(connection.recv(self.BUFF))

        # Extract the info from the incoming message 
        # Extract the public key
        peer_public_key:str = incoming_message_json['public_key_pem']

        # Extract the data 
        # NOTE: assumes the incoming data is in the format as returned by encrypt_message()
        incoming_data:dict = incoming_message_json['data']

        # Decrypt the incoming data
        decrypted_message = decrypt_message(self.priv_key_pem, incoming_data)
        print('Received passcode: ', decrypted_message)

        # Encrypt the passcode using the sender's public key
        encrypted_passcode_msg:dict = encrypt_message(peer_public_key, decrypted_message)

        # Send the encrypted message back 
        print('\033[94mSending response...\033[0m')

        connection.send(json.dumps({
            'code': self.RESP_IDC_CODE, 
            'public_key_pem': self.pub_key_pem,
            'data': encrypted_passcode_msg
        }).encode())

        # Wait for a response and check if we passed
        check_passed:dict = json.loads(connection.recv(self.BUFF).decode())

        # Extract result
        result:bool = check_passed['result'] 

        # Handle result
        if(result):
            self.logger.info("Passed identity check with client (%s)", str(client_address))                   
            return True
        else:
            self.logger.info("Failed identity check with client (%s)", str(client_address))
            return False


    def handle_share_request(self, connection, client_public_key: str, file_information: dict) -> None:  
        """Handles a request to share a file from a client and replys back to the client the results of the share.

        Parameters:
            connection: The connection object to communicate with the client.
            client_public_key (str): The public key of the client, used to identify the storage directory.
            file_information (dict): A dictionary containing the file name and file content.

        Returns:
            None
        """
        # Get the current working directory
        current_directory = os.getcwd()
        
        # Extract the file name and file content from the file_information dictionary
        file_name = file_information["file_name"]
        file_content = file_information["file"]

        # Construct the target directory path using the current directory and the client's public key
        target_directory = os.path.join(current_directory, "Stored_Files", self.get_public_key) # this is the only line that is diffrent from store

        try:
            # Try to change to the target directory
            os.chdir(target_directory)
            self.logger.info("Changed to directory: %s", os.getcwd())
        except FileNotFoundError:
            # Create the directory if it doesn't exist and change to it
            os.makedirs(target_directory)
            os.chdir(target_directory)
            self.logger.info("Directory created and changed to: %s", os.getcwd())
        except Exception as e:
            # Handle other possible exceptions and log the error
            self.logger.error("An error occurred: %s", e)
            return
        
        # Write the file to the target directory and get the message
        message:str = self.write_to_file(file_name, file_content)
        
        # Prepare the outgoing message to be sent to the client
        outgoing_message: dict = {
            'code': self.IDC_CODE,
            'public_key': self.get_public_key,
            'payload': self.encrypt_data(self, client_public_key, message)
        }
        
        # Send the encrypted message to the client
        connection.send(json.dumps(outgoing_message).encode())

    
    def handle_store_request(self, connection, client_public_key: str, file_information: dict) -> None:
        """Handles a request to store a file from a client and replys back to the client the results of the store.

        Parameters:
            connection: The connection object to communicate with the client.
            client_public_key (str): The public key of the client, used to identify the storage directory.
            file_information (dict): A dictionary containing the file name and file content.

        Returns:
            None
        """
        # Get the current working directory
        current_directory = os.getcwd()
        
        # Extract the file name and file content from the file_information dictionary
        file_name = file_information['file_name']
        file_content = file_information["file"]

        # Construct the target directory path using the current directory and the client's public key
        target_directory = os.path.join(current_directory, "Stored_Files", client_public_key)

        try:
            # Try to change to the target directory
            os.chdir(target_directory)
            self.logger.info("Changed to directory: %s", os.getcwd())
        except FileNotFoundError:
            # Create the directory if it doesn't exist and change to it
            os.makedirs(target_directory)
            os.chdir(target_directory)
            self.logger.info("Directory created and changed to: %s", os.getcwd())
        except Exception as e:
            # Handle other possible exceptions and log the error
            self.logger.error("An error occurred: %s", e)
            return
        
        # Write the file to the target directory and get the message
        message:str = self.write_to_file(file_name, file_content)
        
        # Prepare the outgoing message to be sent to the client
        outgoing_message: dict = {
            'code': self.IDC_CODE,
            'public_key': self.get_public_key,
            'payload': self.encrypt_data(self, client_public_key, message)
        }
        
        # Send the encrypted message to the client
        connection.send(json.dumps(outgoing_message).encode())
        
                    
    def handle_delete_request(self, connection, client_public_key: str, file_information: dict) -> None:
        """Handles a request to delete a file from a client dirctory and replys back to the client the results of the delete.

        Parameters:
            connection: The connection object to communicate with the client.
            client_public_key (str): The public key of the client, used to identify the storage directory.
            file_information (dict): A dictionary containing the file name and file content.

        Returns:
            None
        """
        # Get the current working directory
        current_directory = os.getcwd()
        
        # Extract the file name and file content from the file_information dictionary
        file_name = file_information['file_name']
        file_content = file_information["file"]

        # Construct the target directory path using the current directory and the client's public key
        target_directory = os.path.join(current_directory, "Stored_Files", client_public_key)

        try:
            # Try to change to the target directory
            os.chdir(target_directory)
            self.logger.info("Changed to directory: %s", os.getcwd())
        except FileNotFoundError:
            # Create the directory if it doesn't exist and change to it
            os.makedirs(target_directory)
            os.chdir(target_directory)
            self.logger.info("Directory created and changed to: %s", os.getcwd())
        except Exception as e:
            # Handle other possible exceptions and log the error
            self.logger.error("An error occurred: %s", e)
            return
        
        # Write the file to the target directory and get the message
        message:str = self.delete_file(file_name)
        
        # Prepare the outgoing message to be sent to the client
        outgoing_message: dict = {
            'code': self.IDC_CODE,
            'public_key': self.get_public_key,
            'payload': self.encrypt_data(self, client_public_key, message)
        }
        
        # Send the encrypted message to the client
        connection.send(json.dumps(outgoing_message).encode())


    def handle_update_request(self, connection, client_public_key: str, file_information: dict) -> None:
        """Handles a request to update a file from a client and replys back to the client the results of the update.

        Parameters:
            connection: The connection object to communicate with the client.
            client_public_key (str): The public key of the client, used to identify the storage directory.
            file_information (dict): A dictionary containing the file name and file content.

        Returns:
            None
        """
        # Get the current working directory
        current_directory = os.getcwd()
        
        # Extract the file name and file content from the file_information dictionary
        file_name = file_information['file_name']
        file_content = file_information["file"]

        # Construct the target directory path using the current directory and the client's public key
        target_directory = os.path.join(current_directory, "Stored_Files", client_public_key)

        try:
            # Try to change to the target directory
            os.chdir(target_directory)
            self.logger.info("Changed to directory: %s", os.getcwd())
        except FileNotFoundError:
            # Create the directory if it doesn't exist and change to it
            os.makedirs(target_directory)
            os.chdir(target_directory)
            self.logger.info("Directory created and changed to: %s", os.getcwd())
        except Exception as e:
            # Handle other possible exceptions and log the error
            self.logger.error("An error occurred: %s", e)
            return
        
        # Write the file to the target directory and get the message
        message:str = self.update_file(file_name, file_content)
        
        # Prepare the outgoing message to be sent to the client
        outgoing_message: dict = {
            'code': self.IDC_CODE,
            'public_key': self.get_public_key,
            'payload': self.encrypt_data(self, client_public_key, message)
        }
        
        # Send the encrypted message to the client
        connection.send(json.dumps(outgoing_message).encode())
    

    # ---- Methods related to SENDING INFO TO OTHER PEERS ---- #
    # NOTE: the reverse methods of "Methods that HANDLE INCOMING REQUESTS" 

    def send_mcast_hello(self, mcast_group:str, mcast_port:int) -> None:
        """Sends a multicast discovery message to the given group and port.

            Args:
                multicast_group (str): The multicast group IP address.
                port (int): The port number to send the message to.
        """

        # Create the socket
        mcast_sock:socket.socket = socket.socket(
            socket.AF_INET,         # Specify IPv4
            socket.SOCK_DGRAM,      # UDP socket
            socket.IPPROTO_UDP      # UDP protocol 
        )

        # Set the TTL
        mcast_sock.setsockopt(
            socket.IPPROTO_IP,          # Modifying an IP-level setting
            socket.IP_MULTICAST_TTL,    # Setting the mcast TTL
            2                           # TTL
        )

        # Create a message with this machine's common name, IP, and pub key
        message:dict = {
            'public_key_pem': self.pub_key_pem,
            'ip': self.iface,
            'common_name': self.common_name
        }
        
        # Send a multicast message to the multicast group
        mcast_sock.sendto(json.dumps(message).encode(), (mcast_group, mcast_port))
        
        # Info print
        print(f"Server.send_mcast_hello() sent message: {message}")


    def initiate_identity_check(self, connection:socket.socket, peer_public_key_pem:str, client_address:str) -> bool:
        """Complete an identity check handshake with the given connection and client address.
        
        Tasks:
            - Complete the handshake 
            - Log the process and result 

        Returns: 
            (bool) True if the remote peer passes the identity check, False otherwise.
        """

        # Log 
        print(f"\n\t\033[93mStarting Handshake with client ({client_address})\033[0m")   
        
        # Generate a passcode for the handshake
        passcode:str = generate_random_passcode()             

        # Send a messsage with the passcode
        connection.send(json.dumps({
            'code': Server.INIT_IDC_CODE,
            'public_key_pem': self.pub_key_pem,
            'data': encrypt_message(peer_public_key_pem, passcode)
        }).encode())
        
        # Wait for response                                      
        response:dict = json.loads(connection.recv(self.BUFF).decode())

        # Decrypt the incoming response
        client_handshake_data = decrypt_message(
            self.priv_key_pem, 
            response['data']
        )                                       

        # Check that the client supplied the correct passcode
        if(passcode == client_handshake_data):
            # Client passed handshake
            # Log result
            print(f"\t\033[92mClient ({str(client_address)}) returned the correct passcode\033[0m")   

            # End func
            return True
        
        # Client failed handshake if we make it here 
        # Log result
        print("\t\033[91mClient (%s) failed the handshake\033[0m", str(client_address))     

        # Return false to indicate failure
        return False
    

    def send_share_request(self, peer_ip_address:str, plaintext_file:bytes, filename:str) -> None: 
        """Sends a share request to the given client address, and shares the file if ID check is passed."""

        # TODO Step 0: Send basic packet with this client's public key, common name, mac last four, and send share req code (unencrypted packet)
        # TODO ... respond to the incoming ID check 
        # TODO ... if pass, continue | if fail, return error
        
        # TODO Step 1: compute filehash 
        # TODO Step 2: create digital signature 
        # TODO Step 3: create message 
        # TODO Step 4: encrypt message 
        # TODO Step 5: Send encrypted message ... 

        raise NotImplementedError

    
    def send_store_request(self, peer_ip_address:str, plaintext_file:bytes, filename:str) -> None: 
        """Sends a store request to the given client address, and sends the encrypted file if ID check is passed."""

        # TODO Step 0: Send basic packet with this client's public key, common name, mac last four, and send share req code (unencrypted packet)
        # TODO ... respond to the incoming ID check 
        # TODO ... if pass, continue | if fail, return error

        # TODO Step 1: encrypt plaintext file
        # TODO Step 2: compute filehash (of encrypted file)
        # TODO Step 3: create digital signature 
        # TODO Step 4: create message 
        # TODO Step 5: encrypt message 
        # TODO Step 6: Send encrypted message ... 

        raise NotImplementedError

    
    def send_delete_request(self, peer_ip_address:str, filename:str, encrypted_file_hash:str) -> None: 
        """Sends a delete request to the given client address, and tells the remote peer to delete the file if ID check is passed."""

        # TODO Step 0: Send basic packet with this client's public key, common name, mac last four, and send share req code (unencrypted packet)
        # TODO ... respond to the incoming ID check 
        # TODO ... if pass, continue | if fail, return error

        # TODO Step 1: create message 
        # TODO Step 2: encrypt message 
        # TODO Step 3: Send encrypted message ... 

        raise NotImplementedError


    def send_update_request(self, peer_ip_address:str, old_filename:str, new_filename:str, new_plaintext_file:bytes) -> None: 
        """Sends an update request to the given client address, and tells the remote peer to update the file if ID check is passed."""

        # TODO Step 0: Send basic packet with this client's public key, common name, mac last four, and send share req code (unencrypted packet)
        # TODO ... respond to the incoming ID check 
        # TODO ... if pass, continue | if fail, return error

        # TODO Step 1: encrypt plaintext file
        # TODO Step 2: compute filehash (of encrypted file)
        # TODO Step 3: create digital signature 
        # TODO Step 4: create message 
        # TODO Step 5: encrypt message 
        # TODO Step 6: Send encrypted message ... 

        raise NotImplementedError

