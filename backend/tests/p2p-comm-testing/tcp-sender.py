import socket
from configparser import ConfigParser
import json 

# NOTE: actual codes are defined in the Server obj (objects/Server.py)
DISC_CODE:str = "000"
IDC_CODE:str = "001"
SEND_REQ_CODE:str = "101"
STORE_REQ_CODE:str = "102"
DEL_FILE_CODE:str = "103"
UPD_FILE_CODE:str = "104" 


# --- Load config --- #
# Network config for the target port
network_config:ConfigParser = ConfigParser()
network_config.read('config/network.conf')

# Encryption config for identity check
enc_config:ConfigParser = ConfigParser()
enc_config.read('config/encryption.conf')

# Define target IP and get the port from the network config
TARGET_IP:str = '127.0.0.1'
PORT:int = int(network_config['network']['PEER_PORT'])


# --- Init socket --- #
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((TARGET_IP, PORT))


# --- Construct and send message --- #
# Construct the json body to send
message_dict:dict = {
    'code': DISC_CODE
}

# Send the message
client_socket.send(json.dumps(message_dict).encode())

# Close cxn
client_socket.close()
