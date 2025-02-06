

import logging 
import socket
import concurrent.futures 

class server(object):
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)
    socket_connection = socket.socket()
    thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=100)

    
    def __init__(self, server_name, IP_address, port):
        self.sever_name = server_name
        self.IP_address = IP_address
        self.port = port
        self.server_alive = True


    def start_server(self):
        
        '''
        To start the sever I need to pull the allow list of users
        Need to log that I have started the server
        Start main server 
        '''
        
        self.logger.info("Server start up begining")

        '''
        Need to decide how we are going to store the allow list
        Add the code to formate the allow list into the data strut
        '''

        self.socket_connection.bind(self.address, self.port)
        self.logger.info("Socket connection assablishet") 
        #need to add checking and logging to see if the connection failed

        self.socket_connection.listen(5)

        self.logger.info("Server start up complted")

    def running_server(self): 
        '''
        start a thread to get connections
        creat threads for each connection to the server 
        '''
        while(self.server_on):
            cleint, cleint_addresss = self.socket_connection.accept()
            self.logger.info("connection form: %s from address %s", cleint, cleint_addresss)
            self.pool.submit(self.handel_connection(cleint, cleint_addresss))





    def handel_connection(self, cleint, cleint_addresss):
        self.logger.info("Client was is in the allow list")
        ''' Need to make to add the brench of if the user is not allowed in system
        could have the server send a file back to the client stating that it will need to wait for
        the owner to allow the send and add them to the trusted users '''

        #decryte the incoming packets 
        


    
    def shutdown_server(self):
        self.logger.info("Server shutdown started")

        self.thread_pool.shutdown(wait=True)

        '''
        need to updated the allow list of senders 
        '''
        
        self.logger.info("Server shutdown completed")







