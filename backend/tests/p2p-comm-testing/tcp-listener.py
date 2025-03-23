import socket
from configparser import ConfigParser
from utils import now, encrypt_message, decrypt_message, load_key_pem, strip_pem_headers
import json 
import pandas as pd 


# --- Load config --- #
# NOTE: normal ALL_PEERS_CSV path is static 
ALL_PEERS_CSV:str = '../TEST-peer-info/all-peers.csv'

# Network config for listener interface and port 
network_config:ConfigParser = ConfigParser()
network_config.read('config/network.conf')

# Extract the listener interface, port, and buff size from the network config 
IFACE:str = network_config['network']['IFACE']
PORT:int = int(network_config['network']['PEER_PORT'])
BUFF:int = int(network_config['network']['BUFF'])

# Encryption config for identity check
enc_config:ConfigParser = ConfigParser() 
enc_config.read('config/encryption.conf') 

# Load the priv and pub keys
PUBLIC_KEY_PEM:str = load_key_pem(enc_config['paths']['PUB_KEY_PATH'], 'public')
PRIV_KEY_PEM:str = load_key_pem(enc_config['paths']['PRIV_KEY_PATH'], 'private', 'SomeSuperSecurePassphrase')


def initiate_identity_check(connection:socket.socket, client_public_key:str, client_address:str, code:str) -> bool:
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
    passcode:str = "12345"                

    # Send a messsage with the passcode
    connection.send(json.dumps({
        'code': INIT_IDC_CODE,
        'public_key_pem': PUBLIC_KEY_PEM,
        'data': encrypt_message(client_public_key, passcode)
    }).encode())
    
    # Wait for response                                      
    response:dict = json.loads(connection.recv(BUFF).decode())

    # Decrypt the incoming response
    client_handshake_data = decrypt_message(
        PRIV_KEY_PEM, 
        response['data']
    )                                       

    # Check that the client supplied the correct passcode
    if(passcode == client_handshake_data):
        # Client passed handshake
        # Log result
        print(f"\t\033[92mClient ({str(client_address)}) returned the correct passcode\033[0m")   

        # End func
        return True
    
    # Client failed handshake if we make it here 
    # Log result
    print("\t\033[91mClient (%s) failed the handshake\033[0m", str(client_address))     

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

    # -- Handle the incoming message -- # 
    # Extract the JSON and conver to a python dict
    message_json:dict = json.loads(data.decode())
    print(f'\t\033[0mExtracted message JSON: {message_json}')

    # Check for the required keys in the body
    code:int = message_json.get('code', None)
    peer_pub_key_pem:str = message_json.get('public_key_pem', None)
    peer_common_name:str = message_json.get('common_name', None)
    peer_mac_last_four:str = message_json.get('mac_last_four', None)
    
    # If no code or pub key, ignore the message and close the cxn
    if not all([code, peer_pub_key_pem, peer_common_name, peer_mac_last_four]): 
        print('\n\t\033[91mERROR: \033[0mmessage does not contain one of [code, public_key_pem, common_name, mac_last_four] - ignoring message.\033[0m')
        conn.close()
        continue
    
    # Handle the code appropriately
    # DISCOVERY CODE
    if code == DISC_CODE: 
        print('\n\t\033[92mIdentified code: \033[0m"DISCOVERY"\033[0m')

        # Initiate an identity check
        id_check_result:bool = initiate_identity_check(
            conn,               # Open socket connection
            peer_pub_key_pem,   # This pub key pem
            addr[0],            # Peer address
            INIT_IDC_CODE       # Code for initiating an identity check
        )

        # Check result of the identity check
        if id_check_result: 
            
            # Update the all-peers info with the new IP for this peer and set their status to ONLINE
            # Read the existing all_peers_df
            all_peers_df:pd.DataFrame = pd.read_csv(ALL_PEERS_CSV)
            
            # Strip the header and footer from the peer's public key pem and remove quotes and newlines
            peer_pub_key_str:str = strip_pem_headers(peer_pub_key_pem).replace('"', '').replace('\n', '')
            
            # Check if the peer public key exists already
            peer_exists:bool = len(all_peers_df.loc[all_peers_df['peer_pub_key'] == peer_pub_key_str])
            
            # Handle if the peer exists already or not
            if peer_exists: 
                
                # Update the row in the df with the new IP for this peer and mark them as ONLINE
                all_peers_df.loc[all_peers_df['peer_pub_key'] == peer_pub_key_str, ['most_recent_ip', 'online']] = [addr[0], True]

            else: 
                # Peer doesn't exist, so make an entry for them
                new_entry:dict = {
                    'peer_pub_key': peer_pub_key_str, 
                    'online': True,
                    'most_recent_ip': addr[0],
                    'common_name': peer_common_name,
                    'mac_last_four': peer_mac_last_four
                }
                
                # Append the entry to the all peers df
                all_peers_df = pd.concat([all_peers_df, pd.DataFrame([new_entry])], ignore_index=True)
            
            # Resave the all_peers_df
            all_peers_df.to_csv(ALL_PEERS_CSV, index=False)
    
    # RESPOND IDENTITY CHECK CODE
    elif code == RESP_IDC_CODE: 
        print('\t\033[92mIdentified code: \033[0m"RESPOND IDENTITY CHECK"\033[0m')

    # UNRECOGNIZED CODE
    else: 
        print(f'\n\t\033[91mERROR: \033[0mmessage contains an unrecognized code "{code}")\033[0m')

    conn.close()