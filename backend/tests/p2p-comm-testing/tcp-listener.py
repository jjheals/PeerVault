import socket
from configparser import ConfigParser
from utils import now, encrypt_message, decrypt_message, load_key_pem
import json 


# --- Load config --- #
BUFF:int = 2048

# Network config for listener interface and port 
network_config:ConfigParser = ConfigParser()
network_config.read('config/network.conf')

# Extract the listener interface and port from the network config 
IFACE:str = network_config['network']['IFACE']
PORT:int = int(network_config['network']['PEER_PORT'])

# Encryption config for identity check
enc_config:ConfigParser = ConfigParser() 
enc_config.read('config/encryption.conf') 


config_dict = {section: dict(enc_config.items(section)) for section in enc_config.sections()}
print(json.dumps(config_dict, indent=4))


# Load the priv and pub keys
PUBLIC_KEY_PEM:str = load_key_pem(enc_config['paths']['PUB_KEY_PATH'], 'public')
PRIV_KEY_PEM:str = load_key_pem(enc_config['paths']['PRIV_KEY_PATH'], 'private', 'SomeSuperSecurePassphrase')


def initiate_identity_check(connection, client_public_key, client_address, code) -> bool:
    """Complete an identity check handshake with the given connection and client address.
    
    Tasks:
        - Complete the handshake 
        - Log the process and result 

    Returns: 
        (bool) True if the remote peer passes the identity check, False otherwise.
    """

    client_handshake_data = ""           

    # Start the identity check handshake 
    print(f"\033[93mStarting Handshake with client ({client_address})\033[0m")                                                     # Log req
    passcode:str = "12345"                                                                           # Generate a passcode

    # Send a messsage with the passcode
    connection.send(json.dumps({
        'code': INIT_IDC_CODE,
        'public_key_pem': PUBLIC_KEY_PEM,
        'data': encrypt_message(client_public_key, passcode)
    }).encode())      
    
    # Wait for response                                                                             # Send the encrypted passcode
    response:dict = json.loads(connection.recv(BUFF).decode())                                                                     # Wait for an incoming response
    
    print('RESPONSE: ', response)

    # Decrypt the incoming response
    client_handshake_data = decrypt_message(
        PRIV_KEY_PEM, 
        response['data']
    )                                       

    # Check that the client supplied the correct passcode
    if(passcode == client_handshake_data):
        # Client passed handshake
        print("\033[92mClient (%s) returned the correct passcode\033[0m", str(client_address))   # Log result

        # TODO: update the all-peers info with the new IP for this peer and set their status to ONLINE
        # DO SOMETHING ...
        connection.close()

        # End func
        return True
    
    
    # Client failed handshake 
    print("\033[91mClient (%s) failed the handshake\033[0m", str(client_address))     # Log result
    connection.close()

    # Return false to indicate failure
    return False


# NOTE: actual codes are defined in the Server obj (objects/Server.py)
DISC_CODE:str = "000"
INIT_IDC_CODE:str = "011"
RESP_IDC_CODE:str = "012"
SEND_REQ_CODE:str = "101"
STORE_REQ_CODE:str = "102"
DEL_FILE_CODE:str = "103"
UPD_FILE_CODE:str = "104" 


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
    data = conn.recv(BUFF)
    print(f'\t\033[0mMessage: "{data.decode()}"')

    # -- Handle the incoming message -- # 
    # Extract the JSON and conver to a python dict
    message_json:dict = json.loads(data.decode())
    print(f'\t\033[0mExtracted message JSON: {message_json}')

    # Check for a code and pub key pem
    code:int = message_json.get('code', None)
    peer_pub_key_pem:str = message_json.get('public_key_pem', None)

    # If no code or pub key, ignore the message and close the cxn
    if not code or not peer_pub_key_pem: 
        print('\n\t\033[91mERROR: \033[0mmessage does not contain a "code" and/or "public_key_pem" - ignoring message.\033[0m')
        conn.close()
        continue
    
    # If there is a code, handle it appropriately
    if code == DISC_CODE: 
        print('\n\t\033[92mIdentified code: \033[0m"DISCOVERY"\033[0m')

        initiate_identity_check(conn, peer_pub_key_pem, addr[0], INIT_IDC_CODE)

    elif code == RESP_IDC_CODE: 
        print('\t\033[92mIdentified code: \033[0m"RESPOND IDENTITY CHECK"\033[0m')

    else: 
        print(f'\n\t\033[91mERROR: \033[0mmessage contains an unrecognized code "{code}")\033[0m')

    conn.close()