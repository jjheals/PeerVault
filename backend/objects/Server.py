
"""
TODO: 
    - better exception handling so that connections don't hang if an error occurs
    - better logging for successes/failures
    - remove print logs and move to just using Server.logger (self.logger)
"""

import logging 
import socket
import struct
import json
import os
import concurrent.futures 
import pandas as pd
import base64 
from time import sleep

from .DatabaseConnection import DatabaseConnection
from utils import strip_pem_headers, generate_random_passcode, encrypt_message, decrypt_message, now, write_to_file,  \
        hash_bytes_sha256, sign_file, bytes_to_gb, verify_signature, encrypt_bytes_with_aes, decrypt_bytes_with_aes, \
        get_mac_address, setup_logger


class Server(object):

    # DYNAMIC ATTRIBUTES
    common_name:str                     # The common name for this client
    iface:str                           # The interface (address) the server is running on
    pub_key_pem:str                     # This client's public key (with PEM headers)
    priv_key_pem:str                    # This client's private key (with PEM headers)
    symm_aes_key:str                    # The symmetric key used for encrypting/decrypting STORED files (b64 encoded, for bytes do base64.b64decode(self.symm_aes_key))
    db_connection:DatabaseConnection    # Database connection to make queries 
    peer_storage_dir:str                # Path to the directory that contains all peer's stored files (defined in identity config)
    logger:logging.Logger               # For logging
    
    # STATIC ATTRIBUTES
    DISC_CODE:str = "000"       # Code for a discovery message
    INIT_IDC_CODE:str = "011"   # Code for initiating an identity check
    RESP_IDC_CODE:str = "012"   # Code for responding to an identity check
    SHARE_REQ_CODE:str = "101"  # Code for requesting to share a file
    STORE_REQ_CODE:str = "102"  # Code for requesting to store a file
    DEL_FILE_CODE:str = "103"   # Code for requesting to delete a file
    RETR_FILE_CODE:str = "104"  # Code for requesting to retrieve a file
    DONE_CODE:str = "900"       # Code for saying "everything is good, close the connection"
    FAIL_CODE:str = "999"       # Code for failing a verification process (e.g. dig signature)
    BUFF:int = 2048             # Buffer for requests
    REQ_CHECK_SLEEP:int = 2     # Amount of time (in seconds) to wait before checking the status of outgoing requests
    
    
    def __init__(
        self, 
        pub_key_pem:str, 
        priv_key_pem:str, 
        symm_aes_key:str,
        common_name:str, 
        iface:str, 
        port:int,
        mcast_iface:str,
        mcast_port:int,
        mcast_group:str,
        send_db_connection:DatabaseConnection,
        db_filepath:str,
        peer_storage_dir:str,
        log_filepath:str='logs/server.log',
        logger_name:str='server_logger',
        db_log_filepath:str='logs/database.log',
        db_logger_name:str='database_logger'
    ):
        self.pub_key_pem = pub_key_pem
        self.priv_key_pem = priv_key_pem
        self.symm_aes_key = symm_aes_key
        self.common_name = common_name
        self.iface = iface
        self.port = port
        self.mcast_iface = mcast_iface
        self.mcast_port = mcast_port
        self.mcast_group = mcast_group
        self.send_db_connection = send_db_connection
        self.db_filepath = db_filepath
        self.mac_last_four = get_mac_address()[-4:]
        self.peer_storage_dir = peer_storage_dir
        self.db_log_filepath = db_log_filepath
        self.db_logger_name = db_logger_name

        # Init the connection
        self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_alive = False
        
        # Set up logger 
        self.logger = setup_logger(log_filepath, logger_name)
        
        # Init a thread pool
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100) # will limit the server to only 100 threads processing data 

        # Info log
        self.logger.info("Server startup beginning")
        
        # Set the server as alive
        self.server_alive = True
        
        # Info log
        print('\033[92mServer init complete.\033[0m')


    # ---- Methods related to SERVER INITIALIZATION and SHUTDOWN ---- #

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
        
        # Bind the socket to the interface and port
        self.socket_connection.bind((self.iface, self.port))
        self.logger.info("Bound socket connection to address: %s and port %d", self.iface, self.port)

        # Start listening for incoming connections
        self.socket_connection.listen(5)
        
        # Info log
        print('\033[92mServer is now listening for connections.\033[0m')
        self.logger.info("Server is now listening for connections")
        
        # Run the listener while the server is alive
        while(self.server_alive):
            
            # Accept the incoming connection
            cxn, addr = self.socket_connection.accept()

            # Log
            self.logger.info("connection form IP address: %s", str(addr[0])) 
            
            try: 
                
                # Pass connection to handle network req func in a new thread        
                self.thread_pool.submit(self.handle_network_request(
                    cxn, 
                    addr
                ))
                
            except Exception as e: 
                print(f'\033[91mERROR in Server.listen(): \033[0m{e.__class__} -', e)


    def mcast_listen(self) -> None:         
        """Starts a listener for incoming multicast messages."""

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
        sock.bind((self.mcast_iface, self.mcast_port))

        # Pack group and interface together 
        mreq = struct.pack( 
            "4s4s",                                # Pack format 
            socket.inet_aton(self.mcast_group),    # Convert mcast group addr to binary
            socket.inet_aton(self.mcast_iface)     # Convert local interface/addr to binary
        )

        sock.setsockopt(
            socket.IPPROTO_IP,          # Modifying an IP-level setting 
            socket.IP_ADD_MEMBERSHIP,   # Join multicast group
            mreq                        # Group & local interface pack
        )

        # Listen for incoming messages
        # Log
        print("[Multicast Listener] Listening for peer announcements...")
        self.logger.info('Starting multicast listener.')

        # Listen while server is alive
        while self.server_alive:

            # Receive message
            data, addr = sock.recvfrom(1024)  
            peer_info = data.decode()

            # Info print
            print(f"[Listener] New peer discovered: {peer_info}")
            self.logger.info(f'New multicast message from {peer_info}')


            # TODO: handle the new peer 
            # DO SOMETHING ...


    def handle_network_request(self, connection:socket.socket, addr:tuple[str, int]) -> None: 
        """Takes in an incoming connection, the addr info (in the format (ip, port)), checks the requirements of the message, initiates an identity check if required,
        and passes the connection off to the appropriate function.

        Args:
            connection (socket.socket): incomming connection to handle.
            print_info (bool, optional): Specify whether to print info statements to the terminal. Defaults to False.

        """
        
        # Log about the incoming connection
        print(f'\033[0m[{now()}] \033[92mIncoming connection\033[0m')
        print(f'\n\t\033[0mPeer (IP, PORT): {addr}')
        self.logger.info(f'Incoming connection from peer (ip, port): {addr}')

        # Read the incoming data
        data = connection.recv(self.BUFF)

        # Extract the JSON and conver to a python dict
        message_json:dict = json.loads(data.decode())

        # Log
        print(f'\t\033[0mExtracted message JSON: {message_json}')
        self.logger.info(f'Server handle network request got message JSON: {message_json}.')

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
        
        # Strip pem headers from the peer pub key
        peer_pub_key:str = strip_pem_headers(peer_pub_key_pem)       
        
         # Init a DB connection for this thread 
        db_connection:DatabaseConnection = DatabaseConnection(
            self.db_filepath,
            log_filepath=self.db_log_filepath,
            logger_name=self.db_logger_name
        )     
        
        # For simplicity, do the identity check before checking the code
        # NOTE: the only code that doesn't initiate an ID check is an INIT_IDC_CODE
        if code != Server.INIT_IDC_CODE: 
            
            # Do identity check
            id_check_result:bool = self.initiate_identity_check(
                connection, 
                peer_pub_key_pem, 
                addr[0]
            )  

            # If ID check pass, update the peer's info
            if id_check_result: 
                
                # Check if this peer exists already
                # Peer exists, so update their status
                if db_connection.check_peer_exists(peer_pub_key):
                    db_connection.update_peer_status(       
                        peer_pub_key,                     
                        addr[0],
                        new_online_status=True
                    )
                
                # Peer doesn't exist, so create an entry for them
                else: 
                    db_connection.new_peer(
                        peer_pub_key,           # peer_pub_key
                        True,                   # online_status
                        addr[0],                # most_recent_ip
                        peer_common_name,       # common_name
                        peer_mac_last_four      # mac_last_four
                    )
                    
            # If ID check failed, do not respond and do nothing else 
            else: 
                # Log
                print(f'\033[0m[{now()}] \033[93mNOTICE: \033[0mPeer "{addr[0]}" failed the ID check (for DISC code).')
                self.logger.info(f'Peer {addr[0]} failed the ID check - not sending a response.')
                
                # Do not respond
                pass
            
        # If it is an INIT_ID_CODE, then simply respond
        else: 
            self.respond_identity_check(
                connection, 
                addr[0], 
                peer_pub_key_pem, 
                data
            )
            
        # If all required attributes are present, handle the request code appropriately
        match code: 
            
            # Handle discovery code (new peer joined the network)
            case Server.DISC_CODE:
                # NOTE: since we already did ID check and updated the peer's info, do nothing else here
                pass
                
            # Handle identity check code (peer wants us to complete an identity check)
            case Server.INIT_IDC_CODE: 
                # NOTE: we already responded in the conditional before the match statement, so do
                # nothing else here
                pass
            
            # Handle share request code (peer wants to share a file with us)
            case Server.SHARE_REQ_CODE: self.handle_share_request(connection, db_connection)
                    
            # Handle store request code (peer wants to store a file with us)
            case Server.STORE_REQ_CODE: self.handle_store_request(connection, db_connection)
            
            # Handle delete file code (peer wants to delete a file we are storing for them)
            case Server.DEL_FILE_CODE: self.handle_delete_request(connection, db_connection)
            
            # Handle retrieve file code (peer wants the contents of a stored file)
            case Server.RETR_FILE_CODE:
                    self.handle_retrieve_request(
                        connection,
                        strip_pem_headers(peer_pub_key_pem),
                        self.db_connection.cn_from_pub_key(strip_pem_headers(peer_pub_key_pem)),
                        message_json['filename']
                    )
                    
            # Handle other code (invalid)
            case _: 

                # Log 
                print(f'\033[0m[{now()}] \033[93mNOTICE: \033[0mPeer "{addr[0]}" sent an unrecognized code "{code}" - not sending a response.')
                self.logger.info(f'Peer "{addr[0]}" sent an invalid code "{code}" - not sending a response.')

                # Do not respond 
                pass
        
        # Close the connection
        connection.close()


    # ---- Methods that HANDLE INCOMING REQUESTS ---- #    
    # NOTE: the reverse methods of "Methods related to SENDING INFO TO OTHER PEERS"

    def queued_request_checker(self) -> None: 
        """Incrementally checks the queued outgoing requests and sends them if the peer is online."""
        
        # Log
        self.logger.info('Starting queued_request_checker().')
        
        # Run while the server is alive
        while self.server_alive: 
            
            # Log 
            self.logger.info('Checking status of outgoing requests.')
            
            # Get the request IDs for any outgoing requests where the peer is online
            matched_req_ids:list[int] = self.db_connection.check_pending_requests_status(
                'outgoing',
                target_peer_online_status=True
            )

            # Check for results
            if not matched_req_ids or len(matched_req_ids) == 0: 
                # No results
                self.logger.info('in queued_request_checker() - no queued outgoing requests have online peers.')
                continue 

            # Iterate over the matched request IDs
            for req_id in matched_req_ids:

                # Get the info for this request 
                request_info:dict = self.db_connection.get_pending_request(req_id)

                # Make sure we got results to avoid a KeyError
                if not request_info: 
                    self.logger.error(f'in queued_request_checker() - expected to get a matching request for {req_id} but got None.')
                    continue 

                # Extract the peer_pub_key col
                peer_pub_key:str = request_info['peer_pub_key']
                
                # Get this peer's info from the peer info df
                peer_info:dict = self.db_connection.peer_info_from_pub_key(peer_pub_key)
                    
                # Check if this peer is online
                if peer_info['online']: 
                    
                    # Log
                    self.logger.info(f'Sending queued "{request_info["upload_type"].upper()}" request to "{peer_info["common_name"]}.')
                        
                    # Peer is online - extract the other needed attributes for the outgoing req
                    req_type:str = request_info['upload_type']
                    filename:str = request_info['filename']
                        
                    # Act according to the request type
                    match(req_type.lower()): 
                        
                        # SHARE request
                        case 'share': 
                            
                            # Construct the path to the tmp file 
                            tmp_filepath:str = os.path.join('requests', 'tmp', filename)
                    
                            # Get the file contents
                            with open(tmp_filepath, 'rb') as file: 
                                file_contents:bytes = file.read()
                        
                            # Send the share request
                            self.send_share_request(
                                peer_info['most_recent_ip'],    # peer_ip_address
                                file_contents,                  # plaintext_file
                                filename                        # filename
                            )
                            
                            # Delete the tmp file 
                            self.logger.info(f'Sent "{request_info["upload_type"].upper()}" request to "{peer_info["common_name"]} - deleting tmp file at "{tmp_filepath}".')
                            os.remove(tmp_filepath)
                            
                        # STORE request
                        case 'store': 
                            
                            # Construct the path to the tmp file 
                            tmp_filepath:str = os.path.join('requests', 'tmp', filename)
                    
                            # Get the file contents
                            with open(tmp_filepath, 'rb') as file: 
                                file_contents:bytes = file.read()
                        
                            # Send the store request
                            self.send_store_request(
                                peer_info['most_recent_ip'],    # peer_ip_address
                                file_contents,                  # plaintext_file
                                filename                        # filename
                            )

                            # Delete the tmp file 
                            self.logger.info(f'Sent "{request_info["upload_type"].upper()}" request to "{peer_info["common_name"]} - deleting tmp file at "{tmp_filepath}".')
                            os.remove(tmp_filepath)
                            
                        # DELETE request
                        case 'delete': 
                            
                            # Read the currently storing with CSV to get the encrypted file hash
                            curr_storing_with_df:pd.DataFrame = pd.read_csv('peer-info/currently-storing-with.csv')

                            # Find the row with this user and this filename
                            matched_row:pd.DataFrame = curr_storing_with_df.loc[
                                (curr_storing_with_df['peer_pub_key'] == peer_pub_key) & 
                                (curr_storing_with_df['filename'] == filename)
                            ].iloc[0]
                        
                            # Send the share request
                            self.send_delete_request(
                                peer_info['most_recent_ip'],   # peer_ip_address
                                filename,                      # filename
                                matched_row['sha256'],         # encrypted_file_hash
                            )
                            
                            # Log
                            self.logger.info(f'Sent "{request_info["upload_type"].upper()}" request to "{peer_info["common_name"]} - deleting tmp file at "{tmp_filepath}".')

                    # Delete the pending request now that we handled it 
                    self.db_connection.remove_pending_request(req_id)
                    self.logger.info(f'in queued_request_checker() - done handling {request_info["request_type"]} request to peer "{peer_info["common_name"]}" (req ID = {req_id})')

            # NOTE: now done iterating over queued requests 
            # Sleep for Server.REQ_CHECK_SLEEP before next iteration
            sleep(Server.REQ_CHECK_SLEEP)
                
                
    def respond_identity_check(self, connection:socket.socket, client_address:str) -> bool:
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

        # Encrypt the passcode using the sender's public key
        encrypted_passcode_msg:dict = encrypt_message(peer_public_key, decrypted_message)

        # Send the encrypted message back 
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


    def handle_share_request(self, connection:socket.socket, db_connection:DatabaseConnection) -> None:  
        """Handles a request to share a file from a client and replys back to the client the results of the share.

        Parameters:
            connection: The connection object to communicate with the client.
            client_public_key (str): The public key of the client, used to identify the storage directory.
            file_information (dict): A dictionary containing the file name and file content.

        Returns:
            None
        """

        # Read exactly 4 bytes to get the length
        raw_length = connection.recv(4)
        if not raw_length:
            raise ConnectionError("Did not receive length header")

        message_length = struct.unpack('>I', raw_length)[0]

        # Now read the full message
        data = b''
        while len(data) < message_length:
            chunk = connection.recv(self.BUFF)
            if not chunk:
                break
            data += chunk

        # Decode JSON
        response: dict = json.loads(data.decode())
                
        # Decrypt the message
        response_plaintext_dict:dict = json.loads(decrypt_message(self.priv_key_pem, response))
    
        # Extract the file name and file content from the file_information dictionary
        file_name:str = response_plaintext_dict["filename"]
        encoded_file_content:str = response_plaintext_dict["plaintext_file"]
        signature_str:str = response_plaintext_dict['signature']

        # Decode the file content 
        decoded_file_content:str = base64.b64decode(encoded_file_content)

        # Extract the peer's pub key pem from the response dict
        peer_pub_key_pem:str = response_plaintext_dict['public_key_pem']

        # Verify the digital signature
        if not verify_signature(peer_pub_key_pem, decoded_file_content, signature_str):

            # Send a failure message back to the peer
            connection.send({
                'code': Server.FAIL_CODE,
                'public_key_pem': self.pub_key_pem,
                'data': encrypt_message(peer_pub_key_pem, 'Failed digital signature.')
            })

            # Do nothing else
            return 

        # Construct the target directory path
        target_directory:str = 'shared_files'

        # Create the target dir if it doesn't exist
        os.makedirs(target_directory, exist_ok=True)

        # Write the file to the target directory and get the message
        message:str = write_to_file(os.path.join(target_directory, file_name), decoded_file_content)
        
        # Prepare the outgoing message to be sent to the client
        outgoing_message: dict = {
            'code': Server.DONE_CODE,
            'public_key_pem': self.pub_key_pem,
            'data': encrypt_message(peer_pub_key_pem, message)
        }
        
        # Send the encrypted message to the client
        connection.send(json.dumps(outgoing_message).encode())
        
        # If the file was written successfully, add a new entry to the PreviouslySharedWith DB table
        if(message == "File written"):
            
            # Add a new row for the new shared file
            db_connection.new_shared_file(
                strip_pem_headers(peer_pub_key_pem),
                'incoming',
                file_name,
                bytes_to_gb(len(decoded_file_content)),
                hash_bytes_sha256(decoded_file_content)
            )
           
           
    def handle_store_request(self, connection:socket.socket, db_connection:DatabaseConnection) -> None:
        """Handles a request to store a file from a client and replys back to the client the results of the store.

        Parameters:
            connection: The connection object to communicate with the client.
            client_public_key (str): The public key of the client, used to identify the storage directory.
            file_information (dict): A dictionary containing the file name and file content.

        Returns:
            None
        """
        # Read exactly 4 bytes to get the length
        raw_length = connection.recv(4)
        if not raw_length:
            raise ConnectionError("Did not receive length header")

        message_length = struct.unpack('>I', raw_length)[0]

        # Now read the full message
        data = b''
        while len(data) < message_length:
            chunk = connection.recv(self.BUFF)
            if not chunk:
                break
            data += chunk

        # Decode JSON
        response:dict = json.loads(data.decode())
                
        # Decrypt the message
        response_plaintext_dict:dict = json.loads(decrypt_message(self.priv_key_pem, response))
    
        # Extract the file name and file content from the file_information dictionary
        filename:str = response_plaintext_dict["filename"]
        encoded_file_content:str = response_plaintext_dict["encrypted_file"]

        # Decode the file content 
        decoded_encrypted_file_content:str = base64.b64decode(encoded_file_content)

        # Extract the peer's pub key pem and the digital signature from the response dict
        peer_pub_key_pem:str = response_plaintext_dict['public_key_pem']
        signature_str:str = response_plaintext_dict['signature']
        peer_cn:str = db_connection.cn_from_pub_key(strip_pem_headers(peer_pub_key_pem))    # CN is used for info prints and logs
        
        # Verify the digital signature
        if not verify_signature(peer_pub_key_pem, decoded_encrypted_file_content, signature_str):
            
            # Log
            self.logger.warning('in handle_store_request() - request failed the digital signature.')
            
            # Send a failure message back to the peer
            connection.send({
                'code': Server.FAIL_CODE,
                'public_key_pem': self.pub_key_pem,
                'data': encrypt_message(peer_pub_key_pem, 'Failed digital signature.')
            })

            # Do nothing else
            return 
        
        # Construct the target directory path
        target_directory:str = os.path.join(self.peer_storage_dir, response_plaintext_dict['common_name'])

        # Create the target dir if it doesn't exist
        os.makedirs(target_directory, exist_ok=True)

        # Write the file to the target directory and get the message
        message:str = write_to_file(os.path.join(target_directory, filename), decoded_encrypted_file_content)
        
        # Log
        self.logger.info(f'in handle_store_request() - sending response message "{message}" to "{peer_cn}"')
        
        # Prepare the outgoing message to be sent to the client
        outgoing_message: dict = {
            'code': Server.DONE_CODE,
            'public_key_pem': self.pub_key_pem,
            'data': encrypt_message(peer_pub_key_pem, message)
        }
        
        # Send the encrypted message to the client
        connection.send(json.dumps(outgoing_message).encode())

        # If the file write was a success, then add a new entry in the DB
        if(message == "File written"):
            
            # Log
            self.logger.info(f'in handle_store_request() - now storing file "{filename}" for "{peer_cn}"')
            
            # Add a new row for the new shared file
            db_connection.new_storing_for_file(
                strip_pem_headers(peer_pub_key_pem),
                filename,
                bytes_to_gb(len(decoded_encrypted_file_content)),
                hash_bytes_sha256(decoded_encrypted_file_content)
            )
            
                    
    def handle_delete_request(self, connection:socket.socket, db_connection:DatabaseConnection) -> None:
        """
        Handles a request to delete a file from a client and replies back to the client with the results of the delete.

        Parameters:
            connection: The connection object to communicate with the client.
        Returns:
            None
        """

        # Read exactly 4 bytes to get the length
        raw_length = connection.recv(4)
        if not raw_length:
            raise ConnectionError("Did not receive length header")

        message_length = struct.unpack('>I', raw_length)[0]

        # Now read the full message
        data = b''
        while len(data) < message_length:
            chunk = connection.recv(self.BUFF)
            if not chunk:
                break
            data += chunk

        # Decode JSON
        response: dict = json.loads(data.decode())

        # Decrypt the message
        response_plaintext_dict: dict = json.loads(decrypt_message(self.priv_key_pem, response))

        # Extract the file name from the request
        filename: str = response_plaintext_dict["filename"]

        # Extract the peer's public key PEM from the response dict
        peer_pub_key_pem: str = response_plaintext_dict['public_key_pem']   # Pub key WITH PEM headers
        peer_pub_key:str = strip_pem_headers(peer_pub_key_pem)              # Pub key WITHOUT PEM headers

        # Construct path to the stored file
        target_filepath:str = os.path.join(self.peer_storage_dir, response_plaintext_dict['common_name'], filename)
        
        # Attempt to delete the file
        try:

             # Check that we're actually storing this file for this peer
            if not db_connection.check_stored_for_file_exists(peer_pub_key, filename):
                raise FileNotFoundError(f'No matching file "{filename}" found for peer.')
            
            # Remove the entry from the currently storing for CSV
            db_connection.remove_storing_for_entry(
                peer_pub_key,
                filename
            )

            # Delete the stored file 
            os.remove(target_filepath)

            # Send success response
            connection.send(json.dumps({
                'code': Server.DONE_CODE,
                'public_key_pem': self.pub_key_pem,
                'data': encrypt_message(peer_pub_key_pem, json.dumps({'message': 'File deleted successfully.'}))
            }).encode())

        # Handle exceptions
        # File doesn't exist 
        except FileNotFoundError:

            # Log
            self.logger.error(f'File "{target_filepath}" does not exist.')

            # Send error message back
            connection.send(json.dumps({
                'code': Server.FAIL_CODE,
                'public_key_pem': self.pub_key_pem,
                'data': encrypt_message(peer_pub_key_pem, json.dumps({'error': 'File not found'}))
            }).encode())

        # Other exceptions
        except Exception as e:

            # Log
            self.logger.error(f'in handle_delete_request() - error occurred while deleting "{target_filepath}": {e}')

            # Send error message back
            connection.send(json.dumps({
                'code': Server.FAIL_CODE,
                'public_key_pem': self.pub_key_pem,
                'data': encrypt_message(peer_pub_key_pem, json.dumps({'error': 'Error occurred'}))
            }).encode())


    def handle_retrieve_request(self, connection:socket.socket, peer_pub_key_pem:str, peer_cn:str, filename:str) -> None: 
        """Handles incoming requests for retrieving the contents of a stored file. 
        
            Parameters: 
                connection (socket.socket): the socket connection.
                peer_pub_key (str): public key of the peer that initiated the request.
                filename (str): the name of the file that the peer is requesting back.

            Returns: 
                None: sends the file contents (or an error) back to the requesting peer over the given connection.
        """

        # Construct a path to the requested file
        requested_file_path:str = os.path.join(self.peer_storage_dir, peer_cn, filename)

        # Make sure the path exists 
        if not os.path.exists(requested_file_path):

            # Send back an error message
            message_data:str = json.dumps({
                'error': f'The given file name "{filename}" does not exist for peer "{peer_cn}"', 
            })

            # Prepare the outgoing message to be sent to the client
            outgoing_message: dict = {
                'code': Server.FAIL_CODE,
                'public_key_pem': self.pub_key_pem,
                'data': encrypt_message(peer_pub_key_pem, message_data)
            }
        
            # Send the encrypted message to the client
            connection.send(json.dumps(outgoing_message).encode())

        # Read the file to get the (encrypted) contents
        with open(requested_file_path, 'rb') as file:
            encrypted_file_contents:bytes = file.read()
        
        # Prepare the outgoing message to be sent to the client
        outgoing_message: dict = {
            'code': Server.DONE_CODE,
            'public_key_pem': self.pub_key_pem,
            'data': encrypt_message(peer_pub_key_pem, encrypted_file_contents)
        }

        # Prepare the message
        message_bytes:bytes = json.dumps(outgoing_message).encode()
        message_length:bytes = struct.pack('>I', len(message_bytes))  # 4 bytes big-endian

        # Send length first, then message
        connection.sendall(message_length + message_bytes)

        # Close the connection 
        connection.close()


    # ---- Methods related to SENDING INFO TO OTHER PEERS ---- #
    # NOTE: the reverse methods of "Methods that HANDLE INCOMING REQUESTS" 

    def send_mcast_hello(self) -> None:
        """Sends a multicast discovery message to the given group and port.

            Parameters:
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
        mcast_sock.sendto(
            json.dumps(message).encode(), 
            (self.mcast_group, self.mcast_port)
        )
        
        # Info print
        print(f"\n\033[92mServer.send_mcast_hello() sent message: \033[0m\n{message}")


    def find_store_recipient(self, file_size_gb:float) -> str: 
        """
        Sends a multicast message to find a recipient to store a file of the given size.
        
        Parameters: 
            file_size_gb (int): the size of the file that we're trying to store.
            
        Returns: 
            int: an ID that can be used to look up this request later in the queued requests table.
        """
        return NotImplementedError
        
        
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

            # Log result and end func
            self.logger.info(f'in initiate_identity_check() - "{str(client_address)}" returned the correct passcode')
            return True
        
        # Client failed handshake if we make it here 
        self.logger.warning(f'in initiate_identity_check() - "{str(client_address)}" failed the identity handshake')
        return False
    

    def send_share_request(self, peer_ip_address:str, plaintext_file:bytes, filename:str) -> None:
        """Sends a share request to the given client address, and shares the file if ID check is passed."""

        # Create a socket object
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:

            # Connect to the server
            # NOTE: all peers use the same port for their backend server
            client_socket.connect((peer_ip_address, self.port))

            # Log
            self.logger.info(f'Sending share request to "{peer_ip_address}:{self.port}" for file "{filename}"')
            
            # Construct an initial message to send
            message = json.dumps({
                'public_key_pem': self.pub_key_pem,
                'common_name': self.common_name,
                'mac_last_four': self.mac_last_four,
                'code': self.SHARE_REQ_CODE
            })

            # Send the message
            client_socket.send(message.encode())

            # Receive handshake data from the server
            self.logger.info(f'in send_share_request() - received response from peer "{peer_ip_address}" (presumed ID check)')
            response = json.loads(client_socket.recv(self.BUFF))
            
            # Complete the ID check
            passcode = decrypt_message(self.priv_key_pem, response['data'])
            message = json.dumps({
                'public_key_pem': self.pub_key_pem,
                'code': self.RESP_IDC_CODE,
                'data': encrypt_message(response['public_key_pem'], passcode)
            })

            # Send the ID check response
            client_socket.send(message.encode())

            # Compute digital signature
            self.logger.info(f'in send_share_request() - signing file "{filename}"')
            signature:str = base64.b64encode(sign_file(self.priv_key_pem, plaintext_file)).decode('utf-8')
            
            # Create a message with the file contents
            message = json.dumps({
                'public_key_pem': self.pub_key_pem,
                'filename': filename,
                'signature': signature,
                'plaintext_file': base64.b64encode(plaintext_file).decode('utf-8')
            })

            # Encrypt the message with the file data
            enc_message:dict = encrypt_message(response['public_key_pem'], message)

            # Prepare the message
            message_bytes:bytes = json.dumps(enc_message).encode()
            message_length:bytes = struct.pack('>I', len(message_bytes))  # 4 bytes big-endian

            # Send length first, then message
            client_socket.sendall(message_length + message_bytes)

            # Wait for response
            response = json.loads(client_socket.recv(self.BUFF))
            result = decrypt_message(self.priv_key_pem, response['data'])

            # Handle the response message
            # Some unknown error occured on the receiving server
            if(result == "Error occured"): 
                self.logger.error(f'in send_share_request() - an unknown error occured and receiving peer "{peer_ip_address}" was unable to process the request.')
                raise Exception('An unknown error occured and receiving server was unable to process the request.')
            
            # File already exists on the recieving server
            elif(result == "File already exists"):
                self.logger.error(f'in send_share_request() - the receiving peer "{peer_ip_address}" already has a file named "{filename}".')
                raise FileExistsError('Recieving server already has a shared file with the same name.')
            
            # Success result (result == 'File written')
            else: 

                # Log
                self.logger.info('in send_share_request() - successfully shared file "{filename}" with peer "{peer_ip_address}".')
                
                # Get the pub key for this IP address 
                peer_pub_key:str = self.send_db_connection.pub_key_from_ip(peer_ip_address)
                
                # Add a new entry in the DB
                self.send_db_connection.new_shared_file(
                    peer_pub_key,
                    'outgoing',
                    filename,
                    bytes_to_gb(len(plaintext_file)),
                    hash_bytes_sha256(plaintext_file)
                )
        
        # Handle exceptions
        except Exception as e:
            self.logger.error(f'Error in Server.send_share_request(): {e.__class__} - {e}')

        # When everything is done, close the connection
        finally:
            # Close the connection
            client_socket.close()

            # Log
            self.logger.info('in send_share_request() - connection closed"')
    

    def send_store_request(self, peer_ip_address:str, plaintext_file:bytes, filename:str) -> None:
        """Sends a store request to the given client address, and sends the encrypted file if ID check is passed."""

        # Create a socket object
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:

            # Connect to the server
            # NOTE: all peers use the same port for their backend server
            client_socket.connect((peer_ip_address, self.port))

            # Log
            self.logger.info(f'in send_store_request() - sending store request to "{peer_ip_address}:{self.port}"')
            
            # Construct an initial message to send
            message = json.dumps({
                'public_key_pem': self.pub_key_pem,
                'common_name': self.common_name,
                'mac_last_four': self.mac_last_four,
                'code': self.STORE_REQ_CODE
            })

            # Send the message
            client_socket.send(message.encode())

            # Receive handshake data from the server
            self.logger.info('in send_store_request() - received response from peer (presumed ID check).')
            response = json.loads(client_socket.recv(self.BUFF))
            
            # Complete the ID check
            passcode = decrypt_message(self.priv_key_pem, response['data'])
            message = json.dumps({
                'public_key_pem': self.pub_key_pem,
                'code': self.RESP_IDC_CODE,
                'data': encrypt_message(response['public_key_pem'], passcode)
            })

            # Send the ID check response
            client_socket.send(message.encode())
            
            # Log
            self.logger.info('in send_store_request - signing file.')

            # Encrypt the file
            encrypted_file_data:dict = encrypt_bytes_with_aes(
                plaintext_file,
                base64.b64decode(self.symm_aes_key)
            )

            # Get the encrypted file content and nonce from the result
            nonce:str = encrypted_file_data['nonce']
            encrypted_file_contents:str = encrypted_file_data['ciphertext']

            # Sign the encrypted file
            signature:str = base64.b64encode(
                sign_file(
                    self.priv_key_pem, 
                    base64.b64decode(encrypted_file_contents))
            ).decode('utf-8')

            # Create a message with the file contents
            message = json.dumps({
                'common_name': self.common_name,
                'public_key_pem': self.pub_key_pem,
                'filename': filename,
                'signature': signature,
                'encrypted_file': encrypted_file_contents
            })

            # Encrypt the message with the file data
            enc_message:dict = encrypt_message(response['public_key_pem'], message)

            # Prepare the message
            message_bytes:bytes = json.dumps(enc_message).encode()
            message_length:bytes = struct.pack('>I', len(message_bytes))  # 4 bytes big-endian

            # Send length first, then messagesymn_aes_key
            client_socket.sendall(message_length + message_bytes)

            # Wait for response
            response = json.loads(client_socket.recv(self.BUFF))
            result = decrypt_message(self.priv_key_pem, response['data'])

            # Handle the response message
            # Some unknown error occured on the receiving server
            if(json.loads(result).get('error', None) and json.loads(result)['error'] == "Error occured"): 
                raise Exception('An unknown error occured and receiving server was unable to process the request.')
            
            # File already exists on the recieving server
            elif(json.loads(result).get('error', None) and json.loads(result)['error'] == "File already exists"): 
                raise FileExistsError('Recieving server already has a shared file with the same name.')
            
            # Success result (result == 'File written')
            else: 

                # Log
                self.logger.info(f'in send_store_request() - successfully sent "{filename}" to be stored with peer IP "{peer_ip_address}"')

                # Get the peer's public key
                peer_pub_key:str = self.send_db_connection.pub_key_from_ip(peer_ip_address)
                
                # Add a new DB entry
                self.send_db_connection.new_storing_with_file(
                    peer_pub_key,
                    filename,
                    bytes_to_gb(len(encrypted_file_contents)),
                    hash_bytes_sha256(base64.b64decode(encrypted_file_contents)),
                    nonce 
                )
        
        # Handle exceptions
        except Exception as e:
            self.logger.error(f'in send_store_request() - {e.__class__}: {e}')

        # When everything is done, close the connection
        finally:
            client_socket.close()
            self.logger.info(f'in send_store_request() - connection closed.')

    
    def send_delete_request(self, peer_pub_key:str, peer_ip_address:str, filename:str) -> None: 
        """Sends a delete request to the given client address, and tells the remote peer to delete the file if ID check is passed."""

        # Create a socket object
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Connect to the server
        try:

            # NOTE: all peers use the same port for their backend server
            client_socket.connect((peer_ip_address, self.port))

            # Log
            self.logger.info(f'in send_delete_request() - sending delete request to "{peer_ip_address}" for file "{filename}"')
            
            # Construct an initial message to send
            message:str = json.dumps({
                'public_key_pem': self.pub_key_pem,
                'common_name': self.common_name,
                'mac_last_four': self.mac_last_four,
                'code': self.DEL_FILE_CODE
            })

            # Send the message
            client_socket.send(message.encode())

            # Receive handshake data from the server
            self.logger.info(f'in send_delete_request() - received response from peer "{peer_ip_address}" (presumed ID check)')
            response = json.loads(client_socket.recv(self.BUFF))
            
            # Complete the ID check
            passcode = decrypt_message(self.priv_key_pem, response['data'])
            message = json.dumps({
                'public_key_pem': self.pub_key_pem,
                'code': self.RESP_IDC_CODE,
                'data': encrypt_message(response['public_key_pem'], passcode)
            })

            # Send the ID check response
            client_socket.send(message.encode())          

            # Create a message with the file contents
            message = json.dumps({
                'common_name': self.common_name,
                'public_key_pem': self.pub_key_pem,
                'filename': filename
            })

            # Encrypt the message with the file data
            enc_message:dict = encrypt_message(response['public_key_pem'], message)

            # Prepare the message
            message_bytes:bytes = json.dumps(enc_message).encode()
            message_length:bytes = struct.pack('>I', len(message_bytes))  # 4 bytes big-endian

            # Send length first, then payload
            client_socket.sendall(message_length + message_bytes)

            # Wait for response
            response = json.loads(client_socket.recv(self.BUFF))
            result = decrypt_message(self.priv_key_pem, response['data'])

            # Handle the response message
            # Some unknown error occured on the receiving server
            if(result == "Error occurred"): raise Exception('An unknown error occured and receiving server was unable to process the request.')
            
            # File already exists on the recieving server
            elif(result == "File not found"): raise FileNotFoundError('Recieving server can not find a file with the same name.')
            elif(result == "Hash mismatch"): raise Exception('Recieving server has a file with the same name, but the hash does not match.')
            else: 

                # Log
                self.logger.info('in send_delete_request() - successfully deleted "{filename}" from peer "{peer_ip_address}"')

                # Remove this row from the DB table
                self.send_db_connection.remove_storing_with_entry(
                    peer_pub_key,
                    filename                    
                )
        
        # Handle exceptions
        except Exception as e:
            self.logger.error(f'in send_delete_request() - {e.__class__}: {e}')

        # When everything is done, close the connection
        finally:
            client_socket.close()
            self.logger.info('in send_delete_request() - connection closed.')


    def send_retrieve_request(self, peer_pub_key:str, peer_ip_address:str, filename:str, tmp_store_path:str) -> str: 
        """Sends a request to retrieve a file that is currently stored with a peer and saves the contents of the file to the given 
        tmp_store_path, and returns the full file path of the stored file. NOTE: does not request the peer to delete the file,
        just retrieves the file from the peer, decrypts it, and returns the file contents."""

        # Create a socket object
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:

            # Connect to the server
            # NOTE: all peers use the same port for their backend server
            client_socket.connect((peer_ip_address, self.port))

            # Log
            self.logger.info(f'Sending RETRIEVE request to "{peer_ip_address}" for file "{filename}"')
            
            # Construct an initial message to send
            message = json.dumps({
                'public_key_pem': self.pub_key_pem,
                'common_name': self.common_name,
                'mac_last_four': self.mac_last_four,
                'code': self.STORE_REQ_CODE
            })

            # Send the message
            client_socket.send(message.encode())

            # Receive handshake data from the server
            self.logger.info(f'in send_retrieve_request() - received response from peer "{peer_ip_address}" (presumed ID check)')
            response = json.loads(client_socket.recv(self.BUFF))
            
            # Complete the ID check
            passcode = decrypt_message(self.priv_key_pem, response['data'])
            message = json.dumps({
                'public_key_pem': self.pub_key_pem,
                'code': self.RETR_FILE_CODE,
                'data': encrypt_message(response['public_key_pem'], passcode)
            })

            # Send the ID check response
            client_socket.send(message.encode())

            # Wait for response
            response = json.loads(client_socket.recv(self.BUFF))
            result = decrypt_message(self.priv_key_pem, response['data'])

            # Handle the response message
            # Some unknown error occured on the receiving server
            if(result['error'] and result['error'] == "Error occured"): raise Exception('An unknown error occured and receiving server was unable to process the request.')
            
            # Success 
            else: 
                
                 # Create a message with the file name we want
                message = json.dumps({
                    'public_key_pem': self.pub_key_pem,
                    'filename': filename
                })

                # Encrypt the message with the file data
                enc_message:dict = encrypt_message(response['public_key_pem'], message)

                # Prepare the message
                message_bytes:bytes = json.dumps(enc_message).encode()
                message_length:bytes = struct.pack('>I', len(message_bytes))  # 4 bytes big-endian

                # Send length first, then message
                client_socket.sendall(message_length + message_bytes)

                # Wait for response
                response = json.loads(client_socket.recv(self.BUFF))
                result = decrypt_message(self.priv_key_pem, response['data'])
                
                # TODO: Make sure req was successful 
                # DO SOMETHING ... 
                # ... 

                # Extract the encrypted file contents
                encrypted_file_contents:str = result['encrypted_file']

                # Log
                self.logger.log(f'in retrieve_stored_file(): successfully retrieved file "{filename}" from "{peer_ip_address}".')

                # Get the nonce for decrypting
                nonce:str = self.send_db_connection.get_stored_file_nonce(
                    peer_pub_key,
                    filename
                )
                
                # Decode and decrypt the contents 
                decrypted_file_contents:bytes = decrypt_bytes_with_aes(
                    {
                        'nonce': nonce,
                        'ciphertext': encrypted_file_contents
                    },
                    self.symm_aes_key
                )
                
                # Save the file
                os.makedirs(tmp_store_path, exist_ok=True)

                with open(os.path.join(tmp_store_path, filename)) as file: 
                    file.write(decrypted_file_contents)

                # Return the full path
                return os.path.join(tmp_store_path, filename)
            
        # Handle exceptions
        except Exception as e:
            self.logger.error(f'in Server.retrieve_stored_file(): \033[0m{e.__class__}", {e}')
            return ''
