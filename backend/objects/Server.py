import logging 
import socket
import concurrent.futures 

from utils.server_util import * 


class Server(object):

    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)
    socket_connection = socket.socket()
    thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100) # will limit the server to only 100 threads processing data 
    allow_list_dictornary = {1:"localhost"}
    
    def __init__(self, server_name, IP_address, port):
        self.sever_name = server_name
        self.IP_address = IP_address
        self.port = port
        self.server_alive = True

    def server_run_call(self):
        self.server_startup(self)
        self.server_on(self)
        self.server_shutdown(self)

    '''
    Tasks: 
        - Log all start up infomation 
        - Pull list of allowed senders into a dictionary object 
        - bind the socket conntion and the start listening for connections    

    Questions: 
        - Need to think more about what would be good to store in the allow list seaction. The public key of each program should not change with each start but the IP could.
        - On start up should we have the server reach out to update the allow list with the new IP address so that it is up to date 
    '''
    def server_startup(self):
        self.logger.info("Server start up begining")

        #pulling the allow list into the program for look ups 
        allowlist_file = open(r"allowlist.csv", "r") #will need to make the file path right
        list_of_keys = allowlist_file.readlines()
        for key_pair in list_of_keys:
            pair = key_pair.split(":") # will split the text into a list with the delimater of :
            clients_public_key = pair[0]
            clients_ip_address = pair[1]
            self.allow_list_dictornary[clients_public_key] = clients_ip_address
        
        self.logger.info("Pulled %d number of users from allowlist", len(list_of_keys))

        #starts to build the network connections
        self.socket_connection.bind(self.IP_address, self.port)
        self.logger.info("Bound socket contion to address: %s and port %d", self.IP_address, self.port) # Need to add checking to see if it fails to bind to the port and address 

        self.socket_connection.listen(5)
        self.logger.info("Server start up complted")

    '''
    Tasks: 
        - create a loop to take all income network connections and send them off to be handeld by a thread 
        - Log each connection 
        - Make sure things are thread safe 

    Key varables: 
        server_on = this is the varable that can be triggered to shut down the server and stop all incoming connections


    Notes: A client will make one request to the server. If the server needs infomation like the public key from server then it will make it own request to that server 

    '''
    def server_on(self): 
        while(self.server_on):
            cleint, cleint_addresss = self.socket_connection.accept()
            self.logger.info("connection form client: %s and address %s", cleint, cleint_addresss) #string might not be the right data type
            self.thread_pool.submit(self.handel_network_request(cleint, cleint_addresss))


    '''
    Tasks: 
        - Check and see if the client is allowed to send files to this device 
        - Decrypt the incoming packets 
        - Deal with the request
        - close the connection with the client and treminate thread
        - Log all incoming requests and actions

    Questions: What are we doing for the packets that are being sent? Are we having a starnder fromate 
    '''
    def handel_network_request(self, cleint, cleint_addresss):
        if (self.check_allow_list(self)):
            print("decirpt ")
        else:
            self.notify_client(self)
        
        cleint.close()

        
    '''
    Tasks:
        - Check to see if the user is with in the allow list return true if they are in the list and false if they are not in the list 
        - Log result a negative result (should we log all results)

    Things that I will need: the public key of the user with out requesting it. maybe just request it form the device 
    '''
    def check_allow_list(self):
        in_allowlist = False

        return in_allowlist


    def notify_client(self):
        pass


    def client_discovry(self):
        pass

    def store_file(self):
        pass

    def shared_file(self):
        pass

    
    def server_shutdown(self):
        self.logger.info("Server shutdown started")

        self.thread_pool.shutdown(wait=True)

        '''
        need to updated the allow list of senders 
        '''
        
        self.logger.info("Server shutdown completed")