import logging 
import socket
import struct
import json
import os
import concurrent.futures 
import base64 
from time import sleep
import threading as th

from .DatabaseConnection import DatabaseConnection
from utils import strip_pem_headers, generate_random_passcode, encrypt_message, decrypt_message, write_to_file,  \
        hash_bytes_sha256, sign_file, bytes_to_gb, verify_signature, encrypt_bytes_with_aes, decrypt_bytes_with_aes, \
        get_mac_address, setup_logger, format_public_key_pem


class Server(object):

    # DYNAMIC ATTRIBUTES
    common_name:str                         # The common name for this client
    iface:str                               # The interface (address) the server is running on
    pub_key_pem:str                         # This client's public key (with PEM headers)
    priv_key_pem:str                        # This client's private key (with PEM headers)
    symm_aes_key:str                        # The symmetric key used for encrypting/decrypting STORED files (b64 encoded, for bytes do base64.b64decode(self.symm_aes_key))
    send_db_connection:DatabaseConnection   # Database connection to make queries 
    peer_storage_dir:str                    # Path to the directory that contains all peer's stored files (defined in identity config)
    logger:logging.Logger                   # For logging
    temp_dir:str                            # Directory to store temp files, such as files for pending outgoing requests or received as an incoming share request
    
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
    ACC_CODE:str = "123"        # Code for accepting a request 
    WAIT_CODE:str = "124"       # Code for request received but user has not accepted the incoming request (sender has to wait for it to be accepted)
    
    BUFF:int = 2048             # Buffer for requests
    REQ_CHECK_SLEEP:int = 10     # Amount of time (in seconds) to wait before checking the status of requests
        
    
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
        db_logger_name:str='database_logger',
        temp_dir:str='.tmp/'
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
        self.temp_dir = temp_dir
        self.log_filepath = log_filepath
        
        # Init the connection
        self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_alive = False
        
        # Set up logger 
        self.logger = setup_logger(log_filepath, logger_name)
        
        # Init a thread pool
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100) # will limit the server to only 100 threads processing data 

        # Create the temp dir if it doesn't exist
        os.makedirs(temp_dir, exist_ok=True)
        
        # Set the server as alive
        self.server_alive = True
        
        # Info log
        self.logger.info("Server initialized.")


    # ---- Methods related to SERVER INITIALIZATION and SHUTDOWN ---- #

    def start(self) -> bool: 
        """Sets server alive as true, creates threads for self.listen() and self.mcast_listen() AND sends a mcast hello 
        message. Returns True if startup was successful, False otherwise."""
        
        # Set server alive and log
        self.server_alive = True
        self.logger.debug('Starting server startup.')
        
        try: 
            
            # Define threads for the listeners and req handlers
            listen_thread:th.Thread = th.Thread(target=self.listen)
            mcast_thread:th.Thread = th.Thread(target=self.mcast_listen)
            out_req_thread:th.Thread = th.Thread(target=self.handle_pending_outgoing_requests)
            inc_req_thread:th.Thread = th.Thread(target=self.handle_pending_incoming_requests) 
            
            # Start listener and mcast listener
            listen_thread.start()
            mcast_thread.start()
            out_req_thread.start()
            inc_req_thread.start()
            
            # Send MCAST hello message
            self.send_mcast_hello()
            
            # DONE
            self.logger.debug('Server startup successful - now listening for connections.')
            return True
        
        # Handle exceptions 
        except Exception as e: 
            self.logger.error(f'in start() - caught exception. {e.__class__}: {e}')
            return False
        
    
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
        
        # Log
        self.logger.debug('in listen(): starting server listener.')
        
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

            # If this connection is from ourself, ignore it
            if addr == self.iface: 
                self.logger.info('Received loopback message.') 
                continue 
            
            # Log
            self.logger.info(f"Incoming connection form IP address: {str(addr[0])}") 
                
            # Pass connection to handle network req func in a new thread  
            try:  
                self.thread_pool.submit(self.handle_network_request, cxn, addr)


                #self.thread_pool.submit(self.handle_network_request(cxn, addr))
            
            # Handle exceptions that arise during the handle process that are not handled elsewhere 
            except Exception as e: 
                print(f'\033[91mERROR in Server.listen(): \033[0m{e.__class__} -', e)
                self.logger.error(f'in server.listen(): {e.__class__} - {e}')
                

    def mcast_listen(self) -> None:         
        """Starts a listener for incoming multicast messages."""

        # Log
        self.logger.debug('in mcast_listen(): starting MCAST listener.')
        
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
        self.logger.info('Server is now listening for MCAST announcements.')

        # Listen while server is alive
        while self.server_alive:

            try: 
                
                # Receive message
                data, addr = sock.recvfrom(1024)  
                peer_info = data.decode()

                # Extract what we need from the message
                request_info:dict = json.loads(peer_info)
                code:int|str = request_info.get('code', None)
                peer_pub_key_pem:str = request_info.get('pub_key_pem', None)
                peer_ip:str = request_info.get('ip', None)
                peer_cn:str = request_info.get('common_name', None) 
                peer_mac_last_four:str = request_info.get('mac_last_four', None)
                
                # If this is our own address, ignore it
                if addr == self.iface or peer_pub_key_pem == self.pub_key_pem: 
                    self.logger.info('Received loopback MCAST.')
                    continue 
                
                # Info print
                self.logger.info(f'New multicast message: {peer_info}')
                
                # Verify info is given
                if not all([code, peer_pub_key_pem, peer_ip, peer_cn]): 
                    self.logger.warning('Invalid MCAST message (missing required info) - not responding.')
                    continue 

                # Init a new connection to start the ID check
                self.logger.info(f'Initating new connection with "{peer_cn}" at IP "{peer_ip}" for an ID check.')
                connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                connection.connect((peer_ip, self.port))
                
                # Initiate an ID check with the peer
                id_check_result:bool = self.initiate_identity_check(
                    connection,
                    peer_pub_key_pem,
                    peer_ip
                )
                
                # Init a db connection
                db_connection:DatabaseConnection = DatabaseConnection(
                    self.db_filepath,
                    log_filepath=self.db_log_filepath,
                    logger_name=self.db_logger_name
                )   
                
                # Handle ID check result
                peer_pub_key:str = strip_pem_headers(peer_pub_key_pem)
                
                # If ID check pass, update the peer's info
                self.logger.info(f'ID check result for {peer_cn}: {id_check_result}')
                
                if id_check_result: 
                    
                    # Check if this peer exists already
                    # Peer exists, so update their status
                    if db_connection.check_peer_exists(peer_pub_key):
                        self.logger.info(f'Updating status and IP for "{peer_cn}".')
                        
                        db_connection.update_peer_status(       
                            peer_pub_key,                     
                            addr[0],
                            new_online_status=True
                        )
                    
                    # Peer doesn't exist, so create an entry for them
                    else: 
                        self.logger.info(f'Creating new Peer entry for "{peer_cn}".')
                        
                        db_connection.new_peer(
                            peer_pub_key,           # peer_pub_key
                            True,                   # online_status
                            addr[0],                # most_recent_ip
                            peer_cn,                # common_name
                            peer_mac_last_four      # mac_last_four
                        )
                    
                    # Close the connection
                    connection.close()
                    
                # If ID check failed, log and do nothing else 
                else: 
                    self.logger.info(f'Peer {addr[0]} failed the ID check - not sending a response.')
                    connection.close()
                    continue  
            
            # Handle exceptions
            except Exception as e: 
                self.logger.error(f'in mcast_listen(): caught exception. {e.__class__}: {e}')
                continue 
            

    def handle_network_request(self, connection:socket.socket, addr:tuple[str, int]) -> None: 
        """Takes in an incoming connection, the addr info (in the format (ip, port)), checks the requirements of the message, initiates an identity check if required,
        and passes the connection off to the appropriate function.

        Args:
            connection (socket.socket): incomming connection to handle.
            print_info (bool, optional): Specify whether to print info statements to the terminal. Defaults to False.

        """
        
        # Ignore if it is a loopback msg
        if addr[0] == self.iface: return 
        
        # Log about the incoming connection
        self.logger.info(f'in handle_network_request(): incoming connection from peer (ip, port): {addr}')
        
        # Read the incoming data
        data = connection.recv(self.BUFF)

        # Extract the JSON and conver to a python dict
        message_json:dict = json.loads(data.decode())
        self.logger.info(f'in handle_network_request(): incoming message_json (as dict): {message_json}')
        
        # Check for the required keys in the body
        code:int = message_json.get('code', None)
        peer_pub_key_pem:str = message_json.get('pub_key_pem', None)
        peer_common_name:str = message_json.get('common_name', None)
        peer_mac_last_four:str = message_json.get('mac_last_four', None)
        
        # Check if the code is an init ID check
        if code == Server.INIT_IDC_CODE: 
            self.logger.info('in handle_network_request(): incoming request is an INIT_IDC_CODE - responding.')
            
            # Simply respond to the ID check
            self.respond_identity_check(
                connection,                             # connection
                addr[0],                                # client_address
                peer_pub_key_pem,                       # peer_pub_key_pem
                message_json['data']                    # encrypted_data
            )

            # Log
            self.logger.info('in handle_network_request(): done responding to ID check.')
            
            # NOTE: when we get an ID check, we can update the status of that peer since we know they're online
            # and since all requests have an ID check anyway
            
            # Init a DB connection for this thread 
            db_connection:DatabaseConnection = DatabaseConnection(
                self.db_filepath,
                log_filepath=self.db_log_filepath,
                logger_name=self.db_logger_name
            )     
        
            # Check if this peer exists already
            # Peer exists, so update their status
            if db_connection.check_peer_exists(peer_pub_key):
                self.logger.info(f'Updating status and IP for "{peer_common_name}".')
                
                db_connection.update_peer_status(       
                    peer_pub_key,                     
                    addr[0],
                    new_online_status=True
                )
            
            # Peer doesn't exist, so create an entry for them
            else: 
                self.logger.info(f'Creating a new Peer entry for "{peer_common_name}".')
                
                db_connection.new_peer(
                    peer_pub_key,           # peer_pub_key
                    True,                   # online_status
                    addr[0],                # most_recent_ip
                    peer_common_name,       # common_name
                    peer_mac_last_four      # mac_last_four
                )
            
            # NOTE: close the db connection
            db_connection.cursor.close()
            db_connection.cxn.close()
            
            return 
        
        # NOTE: we know at this point that this is not an initiated ID check
        # Close cxn if missing info
        if not all([code, peer_pub_key_pem, peer_common_name, peer_mac_last_four]): 
            self.logger.error(f'in handle_network_request(): message does not contain one of [code, pub_key_pem, common_name, mac_last_four] - ignoring message.')
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
            
        # Do identity check
        self.logger.info(f'in handle_network_request(): initiating ID check with "{addr[0]}"')
        
        id_check_result:bool = self.initiate_identity_check(
            connection, 
            peer_pub_key_pem, 
            addr[0]
        )  

        # Log ID check result
        self.logger.info(f'in handle_network_request(): ID check result for "{addr[0]}": {id_check_result}')
        
        # If ID check pass, update the peer's info
        if id_check_result: 
            
            # Check if this peer exists already
            # Peer exists, so update their status
            if db_connection.check_peer_exists(peer_pub_key):
                self.logger.info(f'Updating status and IP for "{peer_common_name}".')
                
                db_connection.update_peer_status(       
                    peer_pub_key,                     
                    addr[0],
                    new_online_status=True
                )
            
            # Peer doesn't exist, so create an entry for them
            else: 
                self.logger.info(f'Creating a new Peer entry for "{peer_common_name}".')
                
                db_connection.new_peer(
                    peer_pub_key,           # peer_pub_key
                    True,                   # online_status
                    addr[0],                # most_recent_ip
                    peer_common_name,       # common_name
                    peer_mac_last_four      # mac_last_four
                )
                
        # If ID check failed, log and do nothing else 
        else: 
            self.logger.info(f'Peer "{peer_common_name}" ("{addr[0]}") failed the ID check - not sending a response.')
            return 

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
                    db_connection.cn_from_pub_key(strip_pem_headers(peer_pub_key_pem)),
                    message_json['filename']
                )
            
            # Handle accept request code (peer has accepted one of our pending outgoing requests)
            case Server.ACC_CODE: self.handle_accept_request(connection, db_connection)

            # Handle other code (invalid)
            case _: 

                # Log and do not respond
                self.logger.info(f'Peer "{peer_common_name}" ("{addr[0]}") sent an invalid code "{code}" - not sending a response.')
                pass
        
        # Close the connection and DB connection
        connection.close()
        db_connection.cxn.commit()      # Commit just incase
        db_connection.cursor.close()    # Close cursor
        db_connection.cxn.close()       # Close connection
        

    # ---- Methods that HANDLE INCOMING REQUESTS ---- #    
    # NOTE: the reverse methods of "Methods related to SENDING INFO TO OTHER PEERS"

    def handle_pending_outgoing_requests(self) -> None: 
        """Incrementally checks the queued outgoing requests and sends them if the peer is online."""
        # Init a local logger
        logger:logging.Logger = setup_logger(
            os.path.join(os.path.dirname(self.log_filepath), 'server-out-request-handler.log'),
            'server_out_req_logger'
        )
        
        # Log
        logger.info('Starting handle_pending_outgoing_requests().')
        
        # Run while the server is alive
        while self.server_alive: 
            
            # Create a db connection for this thread 
            db_connection:DatabaseConnection = DatabaseConnection(
                self.db_filepath,
                log_filepath=os.path.join(os.path.dirname(self.db_log_filepath), 'server-out-request-db.log'),
                logger_name='server_out_requests_db_logger'
            )
        
            # Log 
            logger.info('Checking status of outgoing requests.')
            
            # Get the request IDs for any outgoing requests where the peer is online
            notified_matched_req_ids:list[int] = db_connection.check_pending_requests_status(
                'outgoing',
                target_peer_online_status=True,
                notified=True
            )
            
            not_notified_matched_req_ids:list[int] = db_connection.check_pending_requests_status(
                'outgoing', 
                target_peer_online_status=True,
                notified=False
            )

            # Combine the two lists
            matched_req_ids:list[int] = notified_matched_req_ids + not_notified_matched_req_ids
            
            # Check for results
            if not matched_req_ids or len(matched_req_ids) == 0: 
                # No results
                logger.info('... no queued outgoing requests have online peers ...')
            else: 
                
                logger.info(f'Found matched request IDs: {matched_req_ids}')
                
                # Iterate over the matched request IDs
                for req_id in matched_req_ids:

                    # Get the info for this request 
                    request_info:dict = db_connection.get_pending_request(req_id)

                    # Make sure we got results to avoid a KeyError
                    if not request_info: 
                        logger.error(f'expected to get a matching request for {req_id} but got None.')
                        continue 
                    
                    # Log
                    logger.info(f'processing outgoing "{request_info["request_type"]}" (ID = {req_id})')

                    # Extract the peer_pub_key and get this peer's info from the Peer table
                    peer_pub_key:str = request_info['peer_pub_key']
                    peer_info:dict = db_connection.peer_info_from_pub_key(peer_pub_key)
                        
                    # Check if this peer is online
                    if peer_info['online']: 
                        
                        # Peer is online - extract the other needed attributes for the outgoing req
                        req_type:str = request_info['request_type']
                        filename:str = request_info['filename']
                        
                        # Log
                        logger.info(f'Sending queued "{req_type.upper()}" request to "{peer_info["common_name"]}.')
                            
                        # Act according to the request type
                        match(req_type.lower()): 
                            
                            # SHARE request
                            case 'share': 
                                
                                # Construct the path to the tmp file 
                                tmp_filepath:str = os.path.join(self.temp_dir, 'outgoing', 'share', filename)
                        
                                # Get the file contents
                                with open(tmp_filepath, 'rb') as file: 
                                    file_contents:bytes = file.read()
                            
                                # Send the share request
                                self.send_share_request(
                                    peer_info['most_recent_ip'],    # peer_ip_address
                                    file_contents,                  # plaintext_file
                                    filename,                       # filename
                                    db_connection
                                )
                                
                            # STORE request
                            case 'store': 
                                
                                # Construct the path to the tmp file 
                                tmp_filepath:str = os.path.join(self.temp_dir, 'outgoing', 'store', filename)
                        
                                # Get the file contents
                                with open(tmp_filepath, 'rb') as file: 
                                    file_contents:bytes = file.read()
                            
                                # Send the store request
                                self.send_store_request(
                                    peer_info['most_recent_ip'],    # peer_ip_address
                                    file_contents,                  # plaintext_file
                                    filename,                       # filename
                                    db_connection
                                )
                                
                            # DELETE request
                            case 'delete': 
                                
                                # Send the delete request
                                self.send_delete_request(
                                    peer_info['most_recent_ip'],   # peer_ip_address
                                    filename,                      # filename
                                    request_info['sha256'],         # encrypted_file_hash
                                    db_connection
                                )

                            # RETRIEVE request
                            case 'retrieve': 
                                
                                # Send the retrieve request
                                self.send_retrieve_request(
                                    peer_info['peer_pub_key'],      # peer_pub_key
                                    peer_info['most_recent_ip'],    # peer_ip_address
                                    filename,                       # filename
                                    os.path.join(self.temp_dir, 'retrieved-files/'),          # tmp_store_path
                                    db_connection
                                )

                
                        # Log
                        logger.info(f'done handling {req_type.upper()} request to peer "{peer_info["common_name"]}" (req ID = {req_id})')

            # NOTE: now done iterating over queued requests 
            logger.debug(f'Sleeping for {Server.REQ_CHECK_SLEEP} seconds before next check.')
            sleep(Server.REQ_CHECK_SLEEP)


    def handle_pending_incoming_requests(self) -> None:
        
        # Init a local logger
        logger:logging.Logger = setup_logger(
            os.path.join(os.path.dirname(self.log_filepath), 'server-in-request-handler.log'),
            'server_in_req_logger'
        )
        
        logger.info('Starting handle_pending_incoming_requests().')

        while self.server_alive:
            
            db_connection: DatabaseConnection = DatabaseConnection(
                self.db_filepath,
                log_filepath=os.path.join(os.path.dirname(self.db_log_filepath), 'server-in-request-db.log'),
                logger_name='server_in_requests_db_logger'
            )
            
            logger.info('Checking status of incoming requests.')
            
            # Get the request IDs for any incoming requests where the peer is online
            notified_matched_req_ids:list[int] = db_connection.check_pending_requests_status(
                'incoming',
                target_peer_online_status=True,
                notified=True
            )
            
            not_notified_matched_req_ids:list[int] = db_connection.check_pending_requests_status(
                'incoming', 
                target_peer_online_status=True,
                notified=False
            )

            # Combine the two lists
            matched_req_ids:list[int] = notified_matched_req_ids + not_notified_matched_req_ids
            
            # Handle results
            if not matched_req_ids:
                logger.info('... no queued incoming requests ...')
            else:
                for req_id in matched_req_ids:
                    request_info = db_connection.get_pending_request(req_id)
                    if not request_info:
                        logger.error(f'... expected to get a matching request for {req_id} but got None.')
                        continue

                    self.logger.info(f'... processing incoming "{request_info["request_type"]}" (ID = {req_id})')

                    if request_info['accepted']:
                        logger.info(f'... found accepted "{request_info["request_type"]}" for "{request_info["filename"]}"')
                        peer_pub_key = request_info['peer_pub_key']
                        peer_info = db_connection.peer_info_from_pub_key(peer_pub_key)

                        if peer_info['online']:
                            logger.info('... peer is ONLINE - sending request.')
                            try:
                                self.send_accepted_message(
                                    peer_pub_key,
                                    peer_info['most_recent_ip'],
                                    request_info['filename'],
                                    request_info['request_type']
                                )
                            except Exception as e:
                                logger.warning(f'... caught exception when sending message. {e.__class__}: {e}')
                        else:
                            logger.info('... peer is OFFLINE - not sending message.')

                        logger.info(f'... done handling request to peer "{peer_info["common_name"]}" (req ID = {req_id})')

            # Sleep after each iteration
            logger.debug(f'Sleeping for {Server.REQ_CHECK_SLEEP} seconds before next check.')
            sleep(Server.REQ_CHECK_SLEEP)



    def respond_identity_check(self, connection:socket.socket, client_address:str, peer_pub_key_pem:str, encrypted_data:str) -> None:
        """Takes in a connection and other info and responds to the incoming identity check."""
        
        # Load the incoming message JSON
        self.logger.info(f'in respond_identity_check(): responding to ID check from "{client_address}"')
        
        # Decrypt the incoming data
        decrypted_message = decrypt_message(self.priv_key_pem, encrypted_data)
        self.logger.debug(f'ID check incoming decrypted message: {decrypted_message}')
        
        # Encrypt the passcode using the sender's public key
        encrypted_passcode_msg:dict = encrypt_message(peer_pub_key_pem, decrypted_message)
        self.logger.debug(f'Sending encrypted message back: {encrypted_passcode_msg}')
        
        # Send the encrypted message back 
        connection.send(json.dumps({
            'code': self.RESP_IDC_CODE, 
            'pub_key_pem': self.pub_key_pem,
            'common_name': self.common_name,
            'mac_last_four': self.mac_last_four,
            'data': encrypted_passcode_msg
        }).encode())

        # NOTE: not expecting a response
        return 

    
    def handle_accept_request(self, connection:socket.socket, db_connection:DatabaseConnection) -> None: 
        """Handles an incoming message that one of our outgoing requests was accepted (or declined) by the peer."""
        self.logger.info('in handle_accept_request(): incoming accept request.')
        
        # Read and decrypt the message
        response_plaintext_dict:dict = json.loads(
            decrypt_message(
                self.priv_key_pem,                      # priv_key_pem
                Server.read_incoming_data(connection)   # encrypted_data
            )
        )

        self.logger.info(f'in handle_accept_request(): got json: {response_plaintext_dict}')
        
        # Extract the needed variables from the response dict 
        peer_pub_key_pem:str = response_plaintext_dict['pub_key_pem']
        filename:str = response_plaintext_dict['filename']
        request_type:str = response_plaintext_dict['request_type']
        accepted_status:bool = response_plaintext_dict['accept']
    
        # Get this request ID from the DB
        request_id:int = db_connection.get_request_id(
            strip_pem_headers(peer_pub_key_pem),
            filename,
            request_type,
            'outgoing'
        )

        self.logger.info(f'in handle_accept_request(): got request ID "{request_id}"')
        
        # Check for a match
        # We didn't get a match, so return a fail code to the peer
        if request_id == -1: 
            self.logger.info('in handle_accept_request(): sending FAIL message back.')
            
            connection.send({
                'code': Server.FAIL_CODE,
                'pub_key_pem': self.pub_key_pem,
                'data': encrypt_message(peer_pub_key_pem, f'Did not find a pending outgoing "{request_type}" request for "{filename}".')
            })

            # Do nothing else
            return

        # Update the accept status for this request ID
        self.logger.info(f'in handle_accept_request(): marking {request_id} as accepted in the DB.')
        db_connection.update_request_accepted(request_id, accepted_status)

        # Send a DONE code back
        connection.send({
            'code': Server.DONE_CODE,
            'pub_key_pem': self.pub_key_pem,
            'data': encrypt_message(peer_pub_key_pem, f'Updated local status of the outgoing "{request_type}" request for "{filename}".')
        })


    def handle_share_request(self, connection:socket.socket, db_connection:DatabaseConnection) -> None:  
        """Handles a request to share a file from a client and replys back to the client the results of the share.

        Parameters:
            connection: The connection object to communicate with the client.
            client_public_key (str): The public key of the client, used to identify the storage directory.
            file_information (dict): A dictionary containing the file name and file content.

        Returns:
            None
        """
        
        try: 
            
            # ---- Read incoming message ---- #
            self.logger.debug('Called handle_share_request()')
            
            # Read and decrypt the incoming data
            response_plaintext_dict:dict = json.loads(
                decrypt_message(
                    self.priv_key_pem, 
                    Server.read_incoming_data(connection)
                )
            )        
            
            # Extract the necessary information from the plaintext dict
            file_name:str = response_plaintext_dict["filename"]                     # Filename
            encoded_file_content:str = response_plaintext_dict["plaintext_file"]    # File contents (b64 encoded)
            signature_str:str = response_plaintext_dict['signature']                # Digital signature 
            decoded_file_content:str = base64.b64decode(encoded_file_content)       # Decoded file content (now plaintext bytes)
            peer_pub_key_pem:str = response_plaintext_dict['pub_key_pem']        # Peer pub key
            peer_cn:str = db_connection.cn_from_pub_key(strip_pem_headers(peer_pub_key_pem))    # NOTE: CN only used for logs
            
            # Log
            self.logger.info(f'in handle_share_request(): handling incoming request for "{peer_cn}" to share "{file_name}"')
            
            # ---- Handle the incoming message ---- #
            
            # Get the request ID from the database 
            # NOTE: DatabaseConnection.get_request_id() returns -1 if the request doesn't exist
            pending_request_id:int = db_connection.get_request_id(strip_pem_headers(peer_pub_key_pem), file_name, 'share', "incoming")
            self.logger.info(f'in handle_share_request(): got pending request ID from DB "{pending_request_id}"')
            
            # Init vars for returning a message to the sender
            outgoing_code:int|str = None
            msg:str = '' 
            
            # Verify the digital signature
            if not verify_signature(peer_pub_key_pem, decoded_file_content, signature_str):
                self.logger.warning(f'in handle_share_request(): "{peer_cn}" failed digital signature for filename "{file_name}"')
                
                # Tell the sender that the request failed
                outgoing_code = Server.FAIL_CODE
                msg = 'Failed digital signature'

            # Check if the request exists and/or is accepted 
            # Request DOES NOT EXIST 
            elif(pending_request_id == -1):
                self.logger.info(f'in handle_share_request(): creating a new pending incoming SHARE request from "{peer_cn}" for "{file_name}"')
                
                # Create an entry for an incoming pending request
                db_connection.new_pending_request(
                    "incoming", 
                    "share", 
                    strip_pem_headers(peer_pub_key_pem), 
                    file_name, 
                    len(decoded_file_content), 
                    signature_str,
                    accepted=None
                )

                # Tell the peer they have to wait
                outgoing_code = Server.WAIT_CODE
                msg = 'Request received, but not yet accepted by the user'

            # Request EXISTS BUT IS NOT ACCEPTED
            elif not db_connection.get_pending_request(pending_request_id)["accepted"]:
                
                # Tell the client that they have to wait 
                outgoing_code = Server.WAIT_CODE
                msg = 'Request not accepted by the user'
                
            # Request EXISTS AND IS ACCEPTED
            else:

                # Construct the target directory path and create it if it doesn't exist
                target_directory:str = os.path.join(self.temp_dir, 'incoming', 'shared')
                os.makedirs(target_directory, exist_ok=True)

                # Write the file to the target directory and get the message
                message:str = write_to_file(os.path.join(target_directory, file_name), decoded_file_content)
                
                # Check if the file was written successfully
                # SUCCESS
                if(message == "File written"):
                    
                    # Add a new row for the new shared file
                    db_connection.new_shared_file(
                        strip_pem_headers(peer_pub_key_pem),
                        'incoming',
                        file_name,
                        bytes_to_gb(len(decoded_file_content)),
                        hash_bytes_sha256(decoded_file_content)
                    )
                    
                    # Log
                    self.logger.info(f'in handle_share_request(): request was handled and new shared file was saved to "{os.path.join(target_directory, file_name)}"')
                    
                    # Tell the sender that everything was processed successfully
                    outgoing_code = Server.DONE_CODE
                    msg = 'Request completed successfully'
                    
                # FAIL 
                else: 
                    
                    # Log
                    self.logger.info(f'in handle_share_request(): there was an error saving file "{file_name}" - write_to_file() returned "{message}"')
                    
                    # Tell the sender that something went wrong and we were unable to process the request 
                    outgoing_code = Server.FAIL_CODE
                    msg = 'There was an error processing the request'

                # Remove the pending request from the DB
                db_connection.remove_pending_request(pending_request_id)
                
                # Tell the sender that the request was successful and is complete 
                outgoing_code = Server.DONE_CODE
                msg = 'Request complete'
                
        finally: 
            # ---- Send response ---- #
            # Prepare the outgoing message to be sent to the client
            self.send_encrypted_message(
                connection, 
                peer_pub_key_pem,
                {
                    "code": outgoing_code,
                    "message": msg
                },
                get_response=False          # We don't need the response 
            )
            
            # Log
            self.logger.info(f'in handle_share_request(): sent message to "{peer_cn}": CODE = {outgoing_code}, MESSAGE = "{msg}"')
        
           
    def handle_store_request(self, connection:socket.socket, db_connection:DatabaseConnection) -> None:
        """Handles a request to store a file from a client and replys back to the client the results of the store.

        Parameters:
            connection: The connection object to communicate with the client.
            client_public_key (str): The public key of the client, used to identify the storage directory.
            file_information (dict): A dictionary containing the file name and file content.

        Returns:
            None
        """

        # ---- Read incoming message ---- #
        self.logger.debug('Called handle_store_request()')
        
        # Read and decrypt the incoming data
        response_plaintext_dict:dict = json.loads(
            decrypt_message(
                self.priv_key_pem, 
                Server.read_incoming_data(connection)
            )
        )        
        
        # Extract the necessary information from the plaintext dict
        filename:str = response_plaintext_dict["filename"]                                  # Filename
        encoded_file_content:str = response_plaintext_dict["encrypted_file"]                # Encrypted file (b64 str)
        decoded_encrypted_file_content:bytes = base64.b64decode(encoded_file_content)       # Decoded encrypted file (bytes)
        peer_pub_key_pem:str = response_plaintext_dict['pub_key_pem']                    # Peer public key PEM
        peer_pub_key:str = strip_pem_headers(peer_pub_key_pem)                              # Peer public key (no PEM headers)
        signature_str:str = response_plaintext_dict['signature']                            # Digital signature
        peer_cn:str = db_connection.cn_from_pub_key(strip_pem_headers(peer_pub_key_pem))    # CN is used for info prints and logs
        
        file_size:float = len(decoded_encrypted_file_content)                   # Size of the encrypted file
        enc_file_hash:str = hash_bytes_sha256(decoded_encrypted_file_content)   # Hash of the encrypted file
        
        # ---- Handle the incoming message ---- #
        
        # Get the request ID from the database 
        # NOTE: DatabaseConnection.get_request_id() returns -1 if the request doesn't exist
        pending_request_id:int = db_connection.get_request_id(strip_pem_headers(peer_pub_key_pem), filename, 'store', "incoming")
        self.logger.info(f'in handle_store_request(): got pending request ID from DB "{pending_request_id}"')
        
        # Init vars for returning a message to the sender
        outgoing_code:int|str = None
        msg:str = '' 
        
        # Verify the digital signature
        if not verify_signature(peer_pub_key_pem, decoded_encrypted_file_content, signature_str):
            self.logger.warning(f'in handle_store_request(): "{peer_cn}" failed digital signature for filename "{filename}"')
            
            # Tell the sender that the request failed
            outgoing_code = Server.FAIL_CODE
            msg = 'Failed digital signature'

        # Check if the request exists and/or is accepted 
        # Request DOES NOT EXIST 
        elif(pending_request_id == -1):
            self.logger.info(f'in handle_store_request(): creating a new pending incoming STORE request from "{peer_cn}" for "{filename}"')
            
            # Create an entry for an incoming pending request
            db_connection.new_pending_request(
                "incoming", 
                "store", 
                peer_pub_key,
                filename, 
                file_size, 
                enc_file_hash,
                accepted=None
            )

            # Tell the peer they have to wait
            outgoing_code = Server.WAIT_CODE
            msg = 'Request received, but not yet accepted by the user'

        # Request EXISTS BUT IS NOT ACCEPTED
        elif not db_connection.get_pending_request(pending_request_id)["accepted"]:
            
            # Tell the client that they have to wait 
            outgoing_code = Server.WAIT_CODE
            msg = 'Request not accepted by the user'
            
        # Request EXISTS AND IS ACCEPTED
        else:

            # Construct the target directory path and create it if it doesn't exist
            target_directory:str = os.path.join(self.peer_storage_dir, peer_cn)
            os.makedirs(target_directory, exist_ok=True)

            # Write the file to the target directory and get the message
            message:str = write_to_file(os.path.join(target_directory, filename), decoded_encrypted_file_content)
            
            # Check if the file was written successfully
            # SUCCESS
            if(message == "File written"):
                
                # Add a new row for the new shared file
                db_connection.new_storing_for_file(
                    peer_pub_key,
                    filename,
                    file_size,
                    enc_file_hash
                )
                
                # Log
                self.logger.info(f'in handle_store_request(): request was handled and new stored file was saved to "{os.path.join(target_directory, filename)}"')
                
                # Tell the sender that everything was processed successfully
                outgoing_code = Server.DONE_CODE
                msg = 'Request completed successfully'
                
            # FAIL 
            else: 
                
                # Log
                self.logger.info(f'in handle_store_request(): there was an error saving file "{filename}" - write_to_file() returned "{message}"')
                
                # Tell the sender that something went wrong and we were unable to process the request 
                outgoing_code = Server.FAIL_CODE
                msg = 'There was an error processing the request'

            # Remove the pending request from the DB
            db_connection.remove_pending_request(pending_request_id)
            
            # Tell the sender that the request was successful and is complete 
            outgoing_code = Server.DONE_CODE
            msg = 'Request complete'
        
        # ---- Send response ---- #
        # Prepare the outgoing message to be sent to the client
        self.send_encrypted_message(
            connection, 
            peer_pub_key_pem,
            {
                "code": outgoing_code,
                "message": msg
            },
            get_response=False          # We don't need the response 
        )
        
        # Log
        self.logger.info(f'in handle_store_request(): sent message to "{peer_cn}": CODE = {outgoing_code}, MESSAGE = "{msg}"')

                              
    def handle_delete_request(self, connection:socket.socket, db_connection:DatabaseConnection) -> None:
        """
        Handles a request to delete a file from a client and replies back to the client with the results of the delete.

        Parameters:
            connection: The connection object to communicate with the client.
        Returns:
            None
        """

        # ---- Read incoming message ---- #
        self.logger.debug('Called handle_delete_request()')
        
        # Read and decrypt the incoming data
        response_plaintext_dict:dict = json.loads(
            decrypt_message(
                self.priv_key_pem, 
                Server.read_incoming_data(connection)
            )
        )        
        
        # Extract the necessary info from the plaintext dict
        filename: str = response_plaintext_dict["filename"]                 # Filename
        peer_pub_key_pem: str = response_plaintext_dict['pub_key_pem']   # Pub key WITH PEM headers
        peer_pub_key:str = strip_pem_headers(peer_pub_key_pem)              # Pub key WITHOUT PEM headers
        peer_cn:str = db_connection.cn_from_pub_key(peer_pub_key)
        
        # ---- Handle the request ---- #
        
        # Construct path to the stored file
        target_filepath:str = os.path.join(self.peer_storage_dir, response_plaintext_dict['common_name'], filename)
        
        # Init vars for the response
        outgoing_code:int|str = None
        msg:str = ''
        
        # Attempt to delete the file
        try:

            # Check that we're actually storing this file for this peer
            # NO MATCH
            if not db_connection.check_stored_for_file_exists(peer_pub_key, filename):
                self.logger.error(f'in handle_delete_request(): no matching file "{filename}" found for "{peer_cn}"')
                
                outgoing_code = Server.FAIL_CODE
                msg = f'No file found matching "{filename}"'
            
            # YES MATCH
            else: 
                # Remove the entry from the CurrentlyStoringFor table in the DB
                db_connection.remove_storing_for_entry(
                    peer_pub_key,
                    filename
                )

                # Delete the stored file 
                os.remove(target_filepath)
                self.logger.info(f'in handle_delete_request(): successfully deleted "{filename}" for "{peer_cn}"')
                
                # Tell the peer that the request was a success
                outgoing_code = Server.DONE_CODE
                msg = f'File "{filename}" was deleted successfully.'
            
        # Handle exceptions
        except Exception as e:
            self.logger.error(f'in handle_delete_request(): {e.__class__} - {e}')
            outgoing_code = Server.FAIL_CODE
            msg = 'Error processing delete request.'
            
        # ---- Send response ---- #
        # Prepare the outgoing message to be sent to the client
        self.send_encrypted_message(
            connection, 
            peer_pub_key_pem,
            {
                "code": outgoing_code,
                "message": msg
            },
            get_response=False          # We don't need the response 
        )
        
        # Log
        self.logger.info(f'in handle_delete_request(): sent message to "{peer_cn}": CODE = {outgoing_code}, MESSAGE = "{msg}"')


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
                'pub_key_pem': self.pub_key_pem,
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
            'pub_key_pem': self.pub_key_pem,
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

        try: 
            
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
                'code': Server.DISC_CODE,
                'pub_key_pem': self.pub_key_pem,
                'ip': self.iface,
                'common_name': self.common_name,
                'mac_last_four': self.mac_last_four
            }
            
            # Send a multicast message to the multicast group
            mcast_sock.sendto(
                json.dumps(message).encode(), 
                (self.mcast_group, self.mcast_port)
            )
            
            # Info print
            self.logger.info('Sent MCAST hello/discovery message.')
            
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in send_mcast_hello(): there was an error sending the multicast hello/discovery message. {e.__class__}: {e}')
            return 
        

    def find_store_recipient(self, file_size_gb:float) -> str: 
        """
        Sends a multicast message to find a recipient to store a file of the given size.
        
        Parameters: 
            file_size_gb (int): the size of the file that we're trying to store.
            
        Returns: 
            int: an ID that can be used to look up this request later in the queued requests table.
        """
        return NotImplementedError
        
        
    def initiate_identity_check(self, connection:socket.socket, peer_pub_key_pem:str, client_address:str) -> bool:
        """Complete an identity check handshake with the given connection and client address.
        
        Tasks:
            - Complete the handshake 
            - Log the process and result 

        Returns: 
            (bool) True if the remote peer passes the identity check, False otherwise.
        """

        # Log 
        self.logger.info(f'in initiate_identity_check(): initiating identity check with "{client_address}".')
        
        # Generate a passcode for the handshake
        passcode:str = generate_random_passcode()             

        # Send a messsage with the passcode
        connection.send(json.dumps({
            'code': Server.INIT_IDC_CODE,
            'pub_key_pem': self.pub_key_pem,
            'data': encrypt_message(peer_pub_key_pem, passcode)
        }).encode())
        
        # Wait for response                
        self.logger.info('in initiate_identity_check(): sent initial message, waiting for response.')                      
        response:dict = json.loads(connection.recv(self.BUFF).decode())

        # Decrypt the incoming response
        self.logger.info('in initiate_identity_check(): reading incoming response.')
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


    def initiate_peer_connection(self, connection:socket.socket, peer_ip_address:str, code:int|str, request_type:str) -> None: 
        """Initiates a connection with the given peer by connecting to the socket, sending an initial message,
        and completing the identity check. Returns the peer's public key PEM from the response."""
        
        # ---- Initial connection ---- #
        # Connect to the peer's backend server
        # NOTE: all peers use the same port for their backend server
        connection.connect((peer_ip_address, self.port))
        self.logger.info(f'in initiate_peer_connection(): sending "{request_type.upper()}" request (code = {code}) to "{peer_ip_address}:{self.port}""')
        
        # Construct an initial message to send
        message = json.dumps({
            'pub_key_pem': self.pub_key_pem,
            'common_name': self.common_name,
            'mac_last_four': self.mac_last_four,
            'code': code
        })

        # Send the message
        connection.send(message.encode())

        # ---- Identity check handshake ---- #
        
        # Receive handshake data from the server
        self.logger.info(f'in initiate_peer_connection() - received response from peer "{peer_ip_address}" (presumed ID check)')
        response = json.loads(connection.recv(self.BUFF))
        
        # Complete the ID check
        passcode = decrypt_message(self.priv_key_pem, response['data'])
        peer_pub_key_pem:str = response['pub_key_pem']
        
        message = json.dumps({
            'pub_key_pem': self.pub_key_pem,
            'code': self.RESP_IDC_CODE,
            'data': encrypt_message(peer_pub_key_pem, passcode)
        })

        # Send the ID check response
        # NOTE: we do not expect a response to our ID check response, but the peer will close the connection if we failed.
        connection.send(message.encode())
        
        # Return the peer's public key pem
        return peer_pub_key_pem
    
    
    def send_encrypted_message(self, connection:socket.socket, peer_pub_key_pem:str, message_payload:dict, get_response:bool=True) -> dict: 
        """Sends an encrypted message over the given connection (encrypted w/ given peer_pub_key_pem). If get_response is True, then 
        this function receives the peer's response, decrypts the response, and returns the response plaintext."""
        
        # Encrypt the given payload
        enc_message:dict = encrypt_message(peer_pub_key_pem, json.dumps(message_payload))

        # Prepare the message
        message_bytes:bytes = json.dumps(enc_message).encode()
        message_length:bytes = struct.pack('>I', len(message_bytes))  # 4 bytes big-endian

        # Send length first, then message
        connection.sendall(message_length + message_bytes)
    
        # Wait for response (if configured)
        if get_response: 
            self.logger.info('in send_encrypted_message(): waiting for response.')
            
            response_plaintext_str:str = decrypt_message(
                self.priv_key_pem, 
                Server.read_incoming_data(connection)
            )
                        
            # Return the response dict
            return json.loads(response_plaintext_str)
    
    
    def send_share_request(self, peer_ip_address:str, plaintext_file:bytes, filename:str, db_connection:DatabaseConnection) -> None:
        """Sends a share request to the given client address, and shares the file if ID check is passed."""

        # Log
        self.logger.info(f'in send_share_request(): sending SHARE request for file "{filename}" to "{peer_ip_address}"')
        
        # Create a socket object
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:

            # ---- Init connection ---- #
            # Init a connection with the peer's backend server (initial message + ID check)
            peer_pub_key_pem:str = self.initiate_peer_connection(
                client_socket, 
                peer_ip_address,
                Server.SHARE_REQ_CODE,
                'share'
            )
            
            # Strip headers from the peer's pub key pem
            peer_pub_key:str = strip_pem_headers(peer_pub_key_pem)
            
            # ---- Send the file information ---- #
            # Send an encrypted message to the peer and get the response
            response:dict = self.send_encrypted_message(
                client_socket,
                peer_pub_key_pem,
                {
                    'pub_key_pem': self.pub_key_pem,
                    'filename': filename,
                    'signature': base64.b64encode(sign_file(self.priv_key_pem, plaintext_file)).decode('utf-8'),
                    'plaintext_file': base64.b64encode(plaintext_file).decode('utf-8')
                }
            )

            # Extract parts of the response for clarity
            response_code:int = response['code']
            response_message:str = response['message']
            
            # Log the response info
            self.logger.info(f'in send_share_request(): got response code "{response_code}" with message "{response_message}"')
            
            # ---- Handle response ---- #             
            match response_code: 
                
                # WAIT code - request was received and processed, but we have to wait
                case Server.WAIT_CODE: 
                    
                    # Check if we already have a pending request for this peer, filename, and request type
                    # NOTE: DatabaseConnection.get_request_id() returns -1 if the request doesn't exist
                    existing_request_id:int = db_connection.get_request_id(peer_pub_key, filename, 'share', 'outgoing') 
                    
                    # Request ALREADY EXISTS 
                    if existing_request_id >= 0: 
                        
                        # Change the "notified" status for this request to TRUE
                        # NOTE: we do not need to create a temp file because it should already exist since the request existed in the DB
                        db_connection.update_request_notified(existing_request_id)
                        self.logger.info(f'in send_share_request(): received WAIT_CODE and request ID "{existing_request_id}" already exists - updated notified to TRUE.')
                        
                    # Request DOES NOT ALREADY EXIST  
                    else:                  
                               
                        # Add the request to PendingRequests in the DB
                        db_connection.new_pending_request(
                            'outgoing', 
                            'share', 
                            peer_pub_key, 
                            filename,
                            bytes_to_gb(len(plaintext_file)),
                            hash_bytes_sha256(plaintext_file)
                        )

                        # Create a temp file for this file so we can send it later 
                        tmp_filepath:str = os.path.join(self.temp_dir, 'outgoing', 'share', filename)
                        
                        # Create the dir for the tmp file if it doesn't exist
                        os.makedirs(os.path.dirname(tmp_filepath), exist_ok=True)
                        
                        # Write the temp file
                        with open(tmp_filepath, 'wb+') as file: 
                            file.write(plaintext_file)
                        
                        # Log
                        self.logger.info(f'in send_share_request(): received WAIT_CODE and request does not exist yet - created entry in PendingRequests and temp file at "{tmp_filepath}"')

                # FAIL code - peer was unable to process the request
                case Server.FAIL_CODE: 
                    
                    # Log and do nothing else
                    self.logger.warning(f'in send_share_request(): something went wrong sending the request (FAIL_CODE) for filename "{filename}" with response message "{response_message}"')
                    return 
            
                # SUCCESS code - peer processed the request and it is all set
                case Server.DONE_CODE: 
                    
                    # Get the request info from the DB
                    request_id:int = db_connection.get_request_id(peer_pub_key, filename, 'share', 'outgoing') 
                    
                    # Change this request to completed in the DB
                    db_connection.completed_pending_request(request_id)
                    
                    # Add a new entry in the PreviouslySharedFiles table
                    db_connection.new_shared_file(
                        peer_pub_key,
                        'outgoing',
                        filename,
                        bytes_to_gb(len(plaintext_file)),
                        hash_bytes_sha256(plaintext_file)
                    )
                    
                    # Remove the temp file if it exists
                    tmp_filepath:str = os.path.join(self.temp_dir, 'outgoing', 'share', filename)
                    
                    if os.path.exists(tmp_filepath):
                        os.remove(tmp_filepath)
                        self.logger.info(f'in send_share_request(): deleted temp file at "{tmp_filepath}"')
                    
                    # Log
                    self.logger.info(f'in send_share_request(): completed request to share "{filename}" (request ID = {request_id})')
                    
        # Handle exceptions
        except Exception as e:
            self.logger.error(f'Error in Server.send_share_request(): {e.__class__} - {e}')

        # When everything is done, close the connection
        finally:
            client_socket.close()
            self.logger.info('in send_share_request() - connection closed"')
    

    def send_store_request(self, peer_ip_address:str, plaintext_file:bytes, filename:str, db_connection:DatabaseConnection) -> None:
        """Sends a store request to the given client address, and sends the encrypted file if ID check is passed."""
        
        # Log
        self.logger.info(f'in send_store_request(): sending STORE request for file "{filename}" to "{peer_ip_address}"')
        
        # Create a socket object
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:

            # ---- Init connection ---- #
            # Init a connection with the peer's backend server (initial message + ID check)
            peer_pub_key_pem:str = self.initiate_peer_connection(
                client_socket, 
                peer_ip_address,
                Server.STORE_REQ_CODE,
                'store'
            )
            
            # Strip headers from the peer's pub key pem
            peer_pub_key:str = strip_pem_headers(peer_pub_key_pem)
            
            # ---- Send the file information ---- #
            # Encrypt the file
            encrypted_file_data:dict = encrypt_bytes_with_aes(
                plaintext_file,
                base64.b64decode(self.symm_aes_key)
            )

            # Get the encrypted file content and nonce from the result
            nonce:str = encrypted_file_data['nonce']
            encrypted_file_contents:str = encrypted_file_data['ciphertext']

            # Hash the encrypted file contents and get the length of the encrypted file contents
            encrypted_file_hash:str = hash_bytes_sha256(base64.b64decode(encrypted_file_contents))
            encrypted_file_size:float = bytes_to_gb(len(base64.b64decode(encrypted_file_contents)))
            
            # Sign the encrypted file
            signature:str = base64.b64encode(
                sign_file(
                    self.priv_key_pem, 
                    base64.b64decode(encrypted_file_contents))
            ).decode('utf-8')
            
            # Send an encrypted message to the peer and get the response
            response:dict = self.send_encrypted_message(
                client_socket,
                peer_pub_key_pem,
                {
                    'pub_key_pem': self.pub_key_pem,
                    'filename': filename,
                    'signature': signature,
                    'encrypted_file': encrypted_file_contents
                }
            )

            # Extract parts of the response for clarity
            response_code:int = response['code']
            response_message:str = response['message']
            
            # Log the response info
            self.logger.info(f'in send_store_request(): got response code "{response_code}" with message "{response_message}"')
            
            # ---- Handle response ---- #             
            # Handle the response message
            match response_code: 
                
                # WAIT code - request was received and processed, but we have to wait
                case Server.WAIT_CODE: 
                    
                    # Check if we already have a pending request for this peer, filename, and request type
                    # NOTE: DatabaseConnection.get_request_id() returns -1 if the request doesn't exist
                    existing_request_id:int = db_connection.get_request_id(peer_pub_key, filename, 'store', 'outgoing') 
                    
                    # Request ALREADY EXISTS 
                    if existing_request_id >= 0: 
                        
                        # Change the "notified" status for this request to TRUE
                        # NOTE: we do not need to create a temp file because it should already exist since the request existed in the DB
                        db_connection.update_request_notified(existing_request_id)
                        self.logger.info(f'in send_store_request(): received WAIT_CODE and request ID "{existing_request_id}" already exists - updated notified to TRUE.')
                        
                    # Request DOES NOT ALREADY EXIST  
                    else:                  
                               
                        # Add the request to PendingRequests in the DB
                        db_connection.new_pending_request(
                            'outgoing', 
                            'store', 
                            peer_pub_key, 
                            filename,
                            encrypted_file_size,
                            encrypted_file_hash
                        )

                        # Create a temp file for this file so we can send it later 
                        tmp_filepath:str = os.path.join(self.temp_dir, 'outgoing', 'store', filename)
                        
                        # Create the dir for the tmp file if it doesn't exist
                        os.makedirs(os.path.dirname(tmp_filepath), exist_ok=True)
                        
                        # Write the temp file
                        with open(tmp_filepath, 'wb+') as file: 
                            file.write(encrypted_file_contents)
                        
                        # Log
                        self.logger.info(f'in send_store_request(): received WAIT_CODE and request does not exist yet - created entry in PendingRequests and temp file at "{tmp_filepath}"')

                # FAIL code - peer was unable to process the request
                case Server.FAIL_CODE: 
                    
                    # Log and do nothing else
                    self.logger.warning(f'in send_store_request(): something went wrong sending the request (FAIL_CODE) for filename "{filename}" with response message "{response_message}"')
                    return 
            
                # SUCCESS code - peer processed the request and it is all set
                case Server.DONE_CODE: 
                    
                    # Get the request info from the DB
                    request_id:int = db_connection.get_request_id(peer_pub_key, filename, 'store', 'outgoing') 
                    
                    # Change this request to completed in the DB
                    db_connection.completed_pending_request(request_id)
                    
                    # Add a new entry in the PreviouslySharedFiles table
                    db_connection.new_storing_with_file(
                        peer_pub_key,
                        filename,                        
                        encrypted_file_size,
                        encrypted_file_hash,
                        nonce
                    )
                    
                    # Remove the temp file if it exists
                    tmp_filepath:str = os.path.join(self.temp_dir, 'outgoing', 'store', filename)
                    
                    if os.path.exists(tmp_filepath):
                        os.remove(tmp_filepath)
                        self.logger.info(f'in send_store_request(): deleted temp file at "{tmp_filepath}"')
                    
                    # Log
                    self.logger.info(f'in send_store_request(): completed request to store "{filename}" (request ID = {request_id})')
        
        # Handle exceptions
        except Exception as e:
            self.logger.error(f'in send_store_request() - {e.__class__}: {e}')

        # When everything is done, close the connection
        finally:
            client_socket.close()
            self.logger.info(f'in send_store_request() - connection closed.')

    
    def send_delete_request(self, peer_pub_key:str, peer_ip_address:str, filename:str, db_connection:DatabaseConnection) -> None: 
        """Sends a delete request to the given client address, and tells the remote peer to delete the file if ID check is passed."""
        
        # Log
        self.logger.info(f'in send_delete_request(): sending DELETE request for file "{filename}" to "{peer_ip_address}"')
        
        # Create a socket object
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Connect to the server
        try:

            # ---- Init connection ---- #
            # Init a connection with the peer's backend server (initial message + ID check)
            peer_pub_key_pem:str = self.initiate_peer_connection(
                client_socket, 
                peer_ip_address,
                Server.DEL_FILE_CODE,
                'delete'
            )
            
            # ---- Send an encrypted message with the file information ---- #
            
            # Send delete request
            response:dict = self.send_encrypted_message(
                client_socket,
                peer_pub_key_pem,
                {
                    'common_name': self.common_name,
                    'pub_key_pem': self.pub_key_pem,
                    'filename': filename
                }
            )

            # Handle the response message
            match response['code']: 
                
                # SUCCESS 
                case Server.DONE_CODE: 
                    
                    # Log
                    self.logger.info(f'in send_delete_request() - successfully deleted "{filename}" from peer "{peer_ip_address}"')

                    # Remove this row from the DB table
                    db_connection.remove_storing_with_entry(
                        peer_pub_key,
                        filename                    
                    )
                
                # FAIL
                case Server.FAIL_CODE: 
                    self.logger.error(f'in send_delete_request(): an error occured (FAIL_CODE) and the receiving server was unable to process the request. Got error: {response["data"]["error"]}')

        # Handle exceptions
        except Exception as e:
            self.logger.error(f'in send_delete_request() - {e.__class__}: {e}')

        # When everything is done, close the connection
        finally:
            client_socket.close()
            self.logger.info('in send_delete_request() - connection closed.')


    def send_retrieve_request(self, peer_pub_key:str, peer_ip_address:str, filename:str, tmp_store_path:str, db_connection:DatabaseConnection) -> str: 
        """Sends a request to retrieve a file that is currently stored with a peer and saves the contents of the file to the given 
        tmp_store_path, and returns the full file path of the stored file. NOTE: does not request the peer to delete the file,
        just retrieves the file from the peer, decrypts it, and returns the file contents."""

        # Log
        self.logger.info(f'in send_share_request(): sending SHARE request for file "{filename}" to "{peer_ip_address}"')
            
        # Create a socket object
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:

            # Connect to the server
            # NOTE: all peers use the same port for their backend server
            client_socket.connect((peer_ip_address, self.port))

            # Construct an initial message to send
            message = json.dumps({
                'pub_key_pem': self.pub_key_pem,
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
                'pub_key_pem': self.pub_key_pem,
                'code': self.RETR_FILE_CODE,
                'data': encrypt_message(response['pub_key_pem'], passcode)
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
                    'pub_key_pem': self.pub_key_pem,
                    'filename': filename
                })

                # Encrypt the message with the file data
                enc_message:dict = encrypt_message(response['pub_key_pem'], message)

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
                nonce:str = db_connection.get_stored_file_nonce(
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

    
    def send_accepted_message(self, peer_pub_key:str, peer_ip_address:str, filename:str, request_type:str) -> None: 
        
        # Log
        self.logger.info(f'in send_accepted_message(): sending ACCEPTED message for file "{filename}" to "{peer_ip_address}"')
        
        # Create a socket object
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # ---- Initial connection ---- #
 
        peer_pub_key_pem:str = self.initiate_peer_connection(
            connection,
            peer_ip_address,
            Server.ACC_CODE,
            'accept'
        )

        # Send the message
        # NOTE: we don't need the response
        self.send_encrypted_message(
            connection,
            peer_pub_key_pem,
            {
                'pub_key_pem': self.pub_key_pem,
                'filename': filename,
                'request_type': request_type,
                'accept': True,
                'code': Server.ACC_CODE
            },
            get_response=False
        )

    
    @staticmethod
    def read_incoming_data(connection:socket.socket) -> dict: 
        """Reads the incoming message from the connection and returns the JSON contents."""

        # Read exactly 4 bytes to get the length
        raw_length = connection.recv(4)
        if not raw_length:
            raise ConnectionError("Did not receive length header")

        # Get the length
        message_length:int = struct.unpack('>I', raw_length)[0]

        # Now read the full message
        data:bytes = b''
        while len(data) < message_length:
            chunk = connection.recv(Server.BUFF)    # Read a chunk of Server.BUFF bytes
            if not chunk: break                     # Exit if there is no data 
            data += chunk                           # Append the chunk contents to the string of data

        # Decode JSON and return
        return json.loads(data.decode())
    
    
    