import socket
from configparser import ConfigParser
from utils import now
import json 

# NOTE: actual codes are defined in the Server obj (objects/Server.py)
DISC_CODE:str = "000"
IDC_CODE:str = "001"
SEND_REQ_CODE:str = "101"
STORE_REQ_CODE:str = "102"
DEL_FILE_CODE:str = "103"
UPD_FILE_CODE:str = "104" 



# --- Load config --- #
# Network config for listener interface and port 
network_config:ConfigParser = ConfigParser()
network_config.read('config/network.conf')

# Extract the listener interface and port from the network config 
IFACE:str = network_config['network']['IFACE']
PORT:int = int(network_config['network']['PEER_PORT'])

# Encryption config for identity check
enc_config:ConfigParser = ConfigParser() 
enc_config.read('config/encryption.conf') 


# --- Init listener socket --- #
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((IFACE, PORT))
server_socket.listen(1)


# --- Listen for incomming messages --- #
while True: 
    print(f'\n\033[0m[{now()}] \033[94mWaiting for a connection...\033[0m')

    # Accept an incoming message
    conn, addr = server_socket.accept()

    # Print a connection message when connection occurs
    print(f'\033[0m[{now()}] \033[92mIncoming connection\033[0m')
    print(f'\n\t\033[0mPeer (IP, PORT): {addr}')

    # Read the incoming data, decode, and print to terminal
    data = conn.recv(1024)
    print(f'\t\033[0mMessage: "{data.decode()}"')

    # -- Handle the incoming message -- # 
    # Extract the JSON and conver to a python dict
    message_json:dict = json.loads(data.decode())
    print(f'\t\033[0mExtracted message JSON: {message_json}')

    # Check for a code 
    code:int = message_json.get('code', None)

    # If no code, ignore the message and close the cxn
    if not code: 
        print('\n\t\033[91mERROR: \033[0mmessage does not contain a "code" - ignoring message.\033[0m')
        conn.close()
        continue
    
    # If there is a code, handle it appropriately
    if code == DISC_CODE: 
        print('\n\t\033[92mIdentified code: \033[0m"DISCOVERY"')
    elif code == IDC_CODE: 
        print('\t\033[92mIdentified code: \033[0m"IDENTITY CHECK"')

    else: 
        print(f'\n\t\033[91mERROR: \033[0mmessage contains an unrecognized code "{code}")')

    conn.close()