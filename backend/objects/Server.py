import logging 
import socket
import struct
import time
import json
import os
import concurrent.futures 
import uuid #mac address 
from datetime import datetime #to get the current time 

from utils.server_util import * 

class Server(object):

    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100) # will limit the server to only 100 threads processing data 

    
    DISC_CODE:str = "000"
    IDC_CODE:str = "001"
    SHARE_REQ_CODE:str = "101"
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
        if self.server_startup():
            self.server_on()
            self.server_shutdown()
        else:
            self.logger.error("Server startup failed. Initialization aborted.")
                

    """
    Purpose:
    Initializes the server, checks for necessary keys, binds the socket, and starts listening for connections.

    Parameters:
    None

    Returns:
    None
    """
    def server_startup(self) -> bool:
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

    """
    Checks if the public and private key files exist and are accessible.

    Returns:
    bool: True if both keys exist and are accessible, False otherwise.
    """
    def check_keys(self) -> bool:

        public_key_path = "path/to/public_key.pem"
        private_key_path = "path/to/private_key.pem"

        try:
            # Check if the public key file exists and is readable
            if not os.path.isfile(public_key_path) or not os.access(public_key_path, os.R_OK):
                self.logger.info("Public key file not found or not readable")
                return False

            # Check if the private key file exists and is readable
            if not os.path.isfile(private_key_path) or not os.access(private_key_path, os.R_OK):
                self.logger.info("Private key file not found or not readable")
                return False

            self.logger.info("Both public and private key files are accessible")
            return True

        except Exception as e:
            self.logger.error("An error occurred while checking keys: %s", e)
            return False

    def generate_keys(self):
        '''
        This is the function that is going to generate the public and priavte keys for the program
        it will also remove a public or private key if the other pair is missing and make a new one

        this could be a problem if someone was able to remove one
        '''

    """ 
    Sends a multicast message and waits for responses.

    Args:
        multicast_group (str): The multicast group IP address.
        port (int): The port number to send the message to.
    """
    def discover_message(self, multicast_group, port):0

        # Create the datagram socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set a timeout so the socket does not block indefinitely when trying to receive data in seconds
        sock.settimeout(10)

        # Set the time-to-live for messages to 1 so they do not go past the local network
        time_to_live = struct.pack('b', 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, time_to_live)

        try:
            # Prepare the payload and message
            payload = {
                "common_name": self.common_name,
                "mac_last_four": self.get_mac_address()
            }

            message = {
                'code': self.IDC_CODE,
                'public_key': self.get_public_key(),
                'payload': json.dumps(payload)
            }
            
            self.logger.info("Sending message: %s", message)
            # Send the message to the multicast group
            sent = sock.sendto(json.dumps(message).encode(), (multicast_group, port))

            # Look for responses from all recipients
            while True:
                self.logger.info("Waiting to receive...")
                try:
                    # Receive data from the socket
                    data, server_address = sock.recvfrom(1024)
                    data = data.decode()
                    self.logger.info("Received data from client (%s): %s", str(server_address), data)
                    # Handle the received data
                    self.responde_identity_check(sock, server_address, self.get_public_key(), data)
                except socket.timeout:
                    self.logger.info("Timed out, no more responses")
                    break
                except Exception as e:
                    self.logger.error("An error occurred: %s", e)
                    break

        except socket.error as e:
            self.logger.error("Socket error: %s", e)
        except Exception as e:
            self.logger.error("An unexpected error occurred: %s", e)
        finally:
            self.logger.info("Closing socket")
            sock.close()

    """
    Returns the MAC address of the current machine.
    """
    def get_mac_address():
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
        incoming_message:dict = []

        while True:
            incoming_message = json.load(connection.recv(1024).decode())# Buffer size is 1024 bytes
            if not incoming_message:
                break
        
        message_code:int    = incoming_message.get('code', None)
        client_public_key   = incoming_message.get("key", None)
        message             = incoming_message.get('payload', None)

        # Handle the message code appropriately
        match message_code: 
            
            # Handle discovery code
            case Server.DISC_CODE:

                # Do identity check
                id_check_result:bool = self.initiate_identity_check(connection, client_public_key, client_address, self.DISC_CODE)  
 
                # If ID check pass, handle the discovery request
                if id_check_result: 
                    self.handle_discovery_code(connection, client_public_key, message, client_address)
                # If ID check failed, do not respond
                else: 
                    pass
            
            # Handle identity check code
            case Server.IDC_CODE: 
                # Complete incoming req for an identity check
                self.responde_identity_check(self, connection, client_address, message) 
            
            # Handle send request code
            case Server.SHARE_REQ_CODE: 

                # Do identity check
                id_check_result:bool = self.initiate_identity_check(connection, client_public_key, client_address, self.SHARE_REQ_CODE)  

                # If ID check pass, handle the discovery request
                if id_check_result: self.handle_share_request(self, message)
                
                # If ID check failed, do not respond
                else: pass
            
            # Handle store request code
            case Server.STORE_REQ_CODE: 
                # Do identity check
                id_check_result:bool = self.initiate_identity_check(connection, client_public_key, client_address, self.STORE_REQ_CODE)  

                # If ID check pass, handle the discovery request
                if id_check_result: self.handle_store_request(connection, client_public_key, message)
                
                # If ID check failed, do not respond
                else: pass
            
            # Handle delete file code
            case Server.DEL_FILE_CODE: 
                # Do handshake
                id_check_result:bool = self.initiate_identity_check(connection, client_public_key, client_address, self.DEL_FILE_CODE)  

                # Delete the file from the system
                if id_check_result: self.handle_delete_request(connection, client_public_key, message)
                # If ID check failed, do not respond
                else: pass

            
            # Handle update file code
            case Server.UPD_FILE_CODE: 
                # Do handshake
                id_check_result:bool = self.initiate_identity_check(connection, client_public_key, client_address, self.UPD_FILE_CODE)  

                # Update the file 
                if id_check_result: self.handle_store_request(connection, client_public_key, message)
                # If ID check failed, do not respond
                else: pass

            
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
                                                     # Log req
        passcode:str = self.generate_passcode(self)
        outgoing_message:dict = {
            'code': self.IDC_CODE,
            'public_key': self.get_public_key,
            'payload': self.encrypt_data(self, client_public_key, passcode)
        }

        connection.send(json.dump(outgoing_message).encode())                                                                                  # Send the encrypted passcode
        ciphertext_message:dict = json.load(connection.recv(1024).decode())    
        message_code:int        = ciphertext_message.get('code', None)
        client_public_key       = ciphertext_message.get("key", None)
        client_handshake_data   = self.decrypt(self.get_private_key(), ciphertext_message.get('payload', None))

        # Check that the client supplied the correct passcode
        if(passcode == client_handshake_data):
            # Client passed handshake
            self.logger.info("Client (%s) returned the correct passcode", str(client_address))  # Log result
            outgoing_message:dict = {
            'code': self.IDC_CODE,
            'public_key': self.get_public_key,
            'payload': self.encrypt_data(self, client_public_key, True)
            }
            connection.send(json.dump(outgoing_message).encode())   
            return True                                                                         # Return that peer passed       
            ''' Do not like how we have mutiple diffrent return statements here'''

        # Client failed handshake 
        self.logger.info("Client (%s) failed the handshake", str(client_address))     # Log result
        outgoing_message:dict = {
            'code': self.IDC_CODE,
            'public_key': self.get_public_key,
            'payload': self.encrypt_data(self, client_public_key, False)
        }
        connection.send(json.dump(outgoing_message).encode())

        return False  
    
    def generate_passcode(self):
        pass

    def get_private_key():
        pass 
    def get_public_key():
        pass 

    def responde_identity_check(self, connection, client_address, client_public_key, ciphertext_message) -> bool:

        self.logger.info("Reviced passcode from client (%s)", str(client_address))                           
        passcode_recived = self.decrypt_data(self.get_private_key, ciphertext_message)

        outgoing_message:dict = {
            'code': self.IDC_CODE,
            'public_key': self.get_public_key,
            'payload': self.encrypt_data(self, client_public_key, passcode_recived)
        }

        connection.send(json.dump(outgoing_message).encode())  

        check_passed:str = connection.recv(1024).decode()                                                                     # Wait for an incoming response
        if(check_passed):
            self.logger.info("Passed identity check with client (%s)", str(client_address))                   
            return True
        else:
            self.logger.info("Failed identity check with client (%s)", str(client_address))
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

        client_mac_address  = client_handshake_data[0:6]
        client_common_name  = client_handshake_data[6:]            

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
                    "max_GB_allowed": 5000000,
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
    
    """
        Handles a request to share a file from a client and replys back to the client the results of the share.

        Parameters:
        connection: The connection object to communicate with the client.
        client_public_key (str): The public key of the client, used to identify the storage directory.
        file_information (dict): A dictionary containing the file name and file content.

        Returns:
        None
        """
    def handle_share_request(self, connection, client_public_key: str, file_information: dict) -> None:
        
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

    """
        Handles a request to store a file from a client and replys back to the client the results of the store.

        Parameters:
        connection: The connection object to communicate with the client.
        client_public_key (str): The public key of the client, used to identify the storage directory.
        file_information (dict): A dictionary containing the file name and file content.

        Returns:
        None
        """
    def handle_store_request(self, connection, client_public_key: str, file_information: dict) -> None:
        
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
        
    """
    Purpose: 
    Writes content to a file.

    Parameters:
    filename (str): The name of the file to write to.
    content (str): The content to be written to the file.

    Returns a string: 
    "File written": no errors in the method
    "File already exists": did not save the file as it is already is storeage
    "Error occured": There was a unexpected error and logs will need to be checked  
    """
    def write_to_file(self, filename, content) -> str:
        try:
            # Check if the file already exists
            if os.path.exists(filename):
                raise FileExistsError(f"File '{filename}' already exists.")
            
            # Write content to the file
            with open(filename, 'w') as file:
                file.write(content)
            self.logger.info("File '%s' written successfully.", filename)
            return "File written"
        
        except FileExistsError as e:
            # Log a warning if the file already exists
            self.logger.warning(e)
            return "File already exists"
        except Exception as e:
            # Log any other exceptions that occur
            self.logger.error("An error occurred: %s", e)
            return "Error occured"
                    
    """
        Handles a request to delete a file from a client dirctory and replys back to the client the results of the delete.

        Parameters:
        connection: The connection object to communicate with the client.
        client_public_key (str): The public key of the client, used to identify the storage directory.
        file_information (dict): A dictionary containing the file name and file content.

        Returns:
        None
        """
    def handle_delete_request(self, connection, client_public_key: str, file_information: dict) -> None:
        
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

    """
    Purpose: 
    Deletes a file from the current directory.

    Parameters:
    filename (str): The name of the file to be deleted.

    Returns:
    bool: True if the file was successfully deleted, False otherwise.
    """
    def delete_file(self, filename: str) -> bool:
        try:
            # Check if the file exists in the current directory
            if os.path.exists(filename):
                # Delete the file
                os.remove(filename)
                self.logger.info("File '%s' deleted successfully.", filename)
                return "File deleted"
            else:
                raise FileNotFoundError(f"File '{filename}' does not exist.")
    
        except FileNotFoundError as e:
            # Log a warning if the file does not exist
            self.logger.warning(e)
            return "File does not exist"
        except Exception as e:
            # Log any other exceptions that occur
            self.logger.error("An error occurred: %s", e)
            return "Error occurred"

    """
    Handles a request to update a file from a client and replys back to the client the results of the update.

    Parameters:
    connection: The connection object to communicate with the client.
    client_public_key (str): The public key of the client, used to identify the storage directory.
    file_information (dict): A dictionary containing the file name and file content.

    Returns:
    None
    """
    def handle_update_request(self, connection, client_public_key: str, file_information: dict) -> None:
        
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
    
    """
    Purpose: 
    Updates the content of a file.

    Parameters:
    filename (str): The name of the file to update.
    content (str): The new content to be written to the file.

    Returns a string: 
    "File updated": no errors in the method
    "File does not exist": did not update the file as it is not in storage
    "Error occurred": There was an unexpected error and logs will need to be checked  
    """
    def update_file(self, filename, content) -> str:
        try:
            # Check if the file exists
            if not os.path.exists(filename):
                raise FileNotFoundError(f"File '{filename}' does not exist.")
            
            # Update content of the file
            with open(filename, 'w') as file:
                file.write(content)
            self.logger.info("File '%s' updated successfully.", filename)
            return "File updated"
        
        except FileNotFoundError as e:
            # Log a warning if the file does not exist
            self.logger.warning(e)
            return "File does not exist"
        except Exception as e:
            # Log any other exceptions that occur
            self.logger.error("An error occurred: %s", e)
            return "Error occurred"

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


    def start_multicast_listener(self, iface:str, port:int): 
        """Starts a thread that listens for incoming multicast messages, performs identity checks, and 
        updates the local database of peer information as appropriate."""
        raise NotImplementedError
