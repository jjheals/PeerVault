import logging 
import socket
import concurrent.futures 

from utils.server_util import * 


class Server(object):

    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)
    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100) # will limit the server to only 100 threads processing data 
    user_list_dictornary = {} # this will hold the public key of the user as the dictionary key and it will hold the users status allowed, blocked or waiting (Defult = waiting)

    
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
        - Pull list of blocked senders into a dictionary object 
        - bind the socket conntion and the start listening for connections    
   '''
    def server_startup(self):
        self.logger.info("Server start up begining")

        #pulling the known users into the program for look ups 
        users = open("users_list.txt", "r") #will need to make the file path right
        user_list = users.readlines() # need to see if there is a problem if the file is empty 
        for key_pair in user_list:
            pair = key_pair.split(":") # will split the text into a list with the delimater of :
            user_public_key = pair[0]
            user_status     = pair[1]
            self.allow_list_dictornary[user_public_key] = user_status
        
        self.logger.info("Pulled %d number of users from userlist", len(user_list))

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

        #takes in the message sent by the client 
        data = ""
        while True: 
            data =+ connection.recv(1024).decode()
            if not data:
                break

        connection.close()

    '''
    Tasks:
        - Check to see if the users status  
        - Log result a negative result (should we log all results)
    '''
    def check_user_list(self, public_key):
        user_allowed = False
        user_access = self.user_list_dictornary[public_key]
        if( user_access == "allowed"):
            user_allowed = True
        elif (user_access == "blocked"):
            #send message to the client that they are not allowed to send messages to the server
            pass
        else:
            #send message to client to hold the files for sending and notify system owner of new users 
            self.user_list_dictornary[public_key] = "waiting" 

        return user_allowed

    def request_public_key(self):
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