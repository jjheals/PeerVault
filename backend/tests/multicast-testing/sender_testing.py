import socket
import time
import json 
import os
import re
import datetime as dt 

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from configparser import ConfigParser


# --- Load config --- #
config:ConfigParser = ConfigParser()
config.read('config/multicast-config.conf')

identity_config:ConfigParser = ConfigParser()
identity_config.read('config/identity.conf')

MCAST_GRP = config['multicast-config']['MCAST_GROUP']           # Multicast group addr
MCAST_PORT = int(config['multicast-config']['MCAST_PORT'])      # Port to listen on
IFACE = config['multicast-config']['LOCAL_IP']                  # Local IP
COMMON_NAME:str = identity_config['IDENTITY']['common_name']    # Common name


# --- Functions --- # 
# NOTE: actual functions defined in ../utils/*

def now() -> str: 
    """Returns the current time as a string for debugging."""
    return dt.datetime.now().strftime('%H:%M:%S')


def load_key(filepath:str, type:str, passphrase:str=None) -> str:
    """Loads the RSA key from the given filepath, where type is 'public' or 'private'."""

    # Check that the filepath exists and is valid
    if not (os.path.exists(filepath) and filepath.endswith('.key')):
        print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mThe given filepath "{filepath}" does not exist or is invalid.')
        return None

    # Read the key file
    with open(filepath, 'rb') as key_file:
        key_data = key_file.read()

        # Read RSA private key
        if type == 'private':
            
            # Make sure a passphrase is given 
            if not passphrase: 
                print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mThe private key is not an RSA key.')
                return None
            
            # Read the key
            try:
                key = serialization.load_pem_private_key(
                    key_data,
                    password=passphrase.encode()
                )

                # Ensure it's an RSA key
                if not isinstance(key, rsa.RSAPrivateKey):
                    print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mThe private key is not an RSA key.')
                    return None

                # Convert the key to a string and return
                return re.sub(
                    r"-----.*KEY-----|\s", "", 
                    key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption(),
                    ).decode()
                )

            except Exception as e:
                print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mFailed to load private key - {e}')
                return None

        # Read RSA public key
        elif type == 'public':
            try:
                key = serialization.load_pem_public_key(key_data)

                # Ensure it's an RSA key
                if not isinstance(key, rsa.RSAPublicKey):
                    print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mThe public key is not an RSA key.')
                    return None

                # Convert the key to a string and return
                return re.sub(
                    r"-----.*KEY-----|\s", "",       
                    key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    ).decode()
                )

            except Exception as e:
                print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mFailed to load public key - {e}')
                return None

        # Invalid type
        else:
            print(f'\033[0m[{now()}] \033[91mERROR in load_key(): \033[0mThe given type "{type}" is not valid.')
            return None

# --- Testing multicast sending --- #
# Create the socket
sock = socket.socket(
    socket.AF_INET,         # Specify IPv4
    socket.SOCK_DGRAM,      # UDP socket
    socket.IPPROTO_UDP      # UDP protocol 
)

# Set the TTL
sock.setsockopt(
    socket.IPPROTO_IP,          # Modifying an IP-level setting
    socket.IP_MULTICAST_TTL,    # Setting the mcast TTL
    2                           # TTL
)

# Send a multicast message with this machine's common name, IP, and pub key
while True:
    
    # Load the public key
    pub_key_str:str = load_key('../TEST-keys/TEST-public.key', 'public') 
    
    message:dict = {
        'public_key': pub_key_str,
        'ip': IFACE,
        'common_name': COMMON_NAME
    }
    
    # Send the message to the multicast group
    sock.sendto(json.dumps(message).encode(), (MCAST_GRP, MCAST_PORT))
    
    print(f"Sent: {message}")
    time.sleep(2)
