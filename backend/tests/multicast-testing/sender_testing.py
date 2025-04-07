import socket
import time
import json 
import os
import re
import datetime as dt 

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from configparser import ConfigParser

# Modify sys path to import utils 
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the parent directory to sys.path
sys.path.insert(0, parent_dir)

# Util imports
from utils import load_key_pem


# --- Load config --- #
# Network config
network_config:ConfigParser = ConfigParser()
network_config.read('../../config/network.conf')

MCAST_GRP = network_config['multicast']['MCAST_GROUP']       # Multicast group addr
MCAST_PORT = int(network_config['multicast']['MCAST_PORT'])  # Port to listen on
IFACE = network_config['multicast']['LOCAL_IP']              # Local IP

# Identity config
identity_config:ConfigParser = ConfigParser()
identity_config.read('../../config/identity.conf')

COMMON_NAME:str = identity_config['IDENTITY']['common_name']    # Common name

# Encryption config 
# NOTE: using static path relative to this script rather than the paths in enc config
#enc_config:ConfigParser = ConfigParser()
#enc_config.read('../../config/encryption.conf')

PUBLIC_KEY_PEM:str = load_key_pem('../TEST-keys/TEST-public.key', 'public')


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
    
    # Construct the message    
    message:dict = {
        'public_key': PUBLIC_KEY_PEM,
        'ip': IFACE,
        'common_name': COMMON_NAME
    }
    
    # Send the message to the multicast group
    sock.sendto(json.dumps(message).encode(), (MCAST_GRP, MCAST_PORT))
    
    print(f"Sent: {message}")
    time.sleep(2)
