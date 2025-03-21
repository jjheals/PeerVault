import socket
from configparser import ConfigParser
import json 
from utils import load_key_pem, encrypt_message, decrypt_message, now


# NOTE: actual codes are defined in the Server obj (objects/Server.py)
DISC_CODE:str = "000"
INIT_IDC_CODE:str = "011"
RESP_IDC_CODE:str = "012"
SEND_REQ_CODE:str = "101"
STORE_REQ_CODE:str = "102"
DEL_FILE_CODE:str = "103"
UPD_FILE_CODE:str = "104" 


# --- Load config --- #
BUFF:int = 2048

# Network config for the target port
network_config:ConfigParser = ConfigParser()
network_config.read('config/network.conf')

# Encryption config for identity check
enc_config:ConfigParser = ConfigParser()
enc_config.read('config/encryption.conf')

PUBLIC_KEY_PEM:str = load_key_pem(enc_config['paths']['PUB_KEY_PATH'], 'public')
PRIV_KEY_PEM:str = load_key_pem(enc_config['paths']['PRIV_KEY_PATH'], 'private', 'SomeSuperSecurePassphrase')


# Define target IP and get the port from the network config
TARGET_IP:str = '127.0.0.1'
PORT:int = int(network_config['network']['PEER_PORT'])


# --- Init socket --- #
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((TARGET_IP, PORT))


# --- Construct and send message --- #
# Construct the json body to send
message_dict:dict = {
    'code': DISC_CODE,
    'public_key_pem': PUBLIC_KEY_PEM
}

# Send the discovery message
client_socket.send(
    json.dumps(message_dict).encode()
)

# Wait for a response 
# Load the incoming message JSON
incoming_message_json:dict = json.loads(client_socket.recv(BUFF))
print(incoming_message_json)

# Extract the info from the incoming message 
# TODO: check the code 
# NOTE: for now assume it is an INIT_IDC_CODE

# Extract the public key
peer_public_key:str = incoming_message_json['public_key_pem']

# Extract the data 
# NOTE: assumes the incoming data is in the format as returned by encrypt_message()
incoming_data:dict = incoming_message_json['data']

# Decrypt the incoming data
decrypted_message = decrypt_message(PRIV_KEY_PEM, incoming_data)
print('Received passcode: ', decrypted_message)

# Encrypt the passcode using the sender's public key
encrypted_passcode_msg:dict = encrypt_message(peer_public_key, decrypted_message)

# Send the encrypted message back 
print('\033[94mSending response...\033[0m')

client_socket.send(json.dumps({
    'code': RESP_IDC_CODE, 
    'public_key_pem': PUBLIC_KEY_PEM,
    'data': encrypted_passcode_msg
}).encode())