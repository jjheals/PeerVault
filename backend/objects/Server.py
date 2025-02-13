import logging 
import socket
import json
import concurrent.futures 

from utils.server_util import * 


class Server(object):

    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100) # will limit the server to only 100 threads processing data 

    
    def __init__(self, server_name, IP_address, port):
        self.sever_name = server_name
        self.IP_address = IP_address
        self.port = port
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
        - bind the socket conntion and the start listening for connections    
   '''
    def server_startup(self):
        self.logger.info("Server start up begining")

        #check if the keys exist 

        #starts to build the network connections
        self.socket_connection.bind(self.IP_address, self.port)
        self.logger.info("Bound socket contion to address: %s and port %d", self.IP_address, self.port) # Need to add checking to see if it fails to bind to the port and address 

        self.socket_connection.listen(5)
        self.logger.info("Server start up complted")
        self.server_alive = True

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
        - Set up the script to run so that we can allow multicast connections on the device 
    '''
    def client_discovry(self):
        pass

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
        while work_to_be_done: 
            data = ""
            while True: 
                data =+ connection.recv(1024).decode()
                if not data:
                    break

            #read and do the stats code

        connection.close()

    '''
    Tasks:
        - Complete the handshake 
        - Log the process and result 
    '''
    def client_server_handshake(self, connection, cleint_address):
        handshake_complete = False

        while True: 
            data = ""
            while True: 
                data =+ connection.recv(1024).decode()
                if not data:
                    break
        #look at notes for the steps of the handshake 

        return handshake_complete

    def store_file(self):
        pass

    def shared_file(self):
        pass

    
    def server_shutdown(self):
        self.logger.info("Server shutdown started")

        self.thread_pool.shutdown(wait=True)
        
        self.logger.info("Server shutdown completed")