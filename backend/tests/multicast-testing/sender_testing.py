import socket
import time
import json 
import os
import re
import datetime as dt 

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from configparser import ConfigParser

# Add the parent directory to sys.path for util and object imports 
import sys
import os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, parent_dir)

# Finish imports    
from objects import Server 
from utils import load_key_pem


# ---- Load config ---- # 
enc_config:ConfigParser = ConfigParser()
enc_config.read('../../config/encryption.conf')

network_config:ConfigParser = ConfigParser()
network_config.read('../../config/network.conf')

identity_config:ConfigParser = ConfigParser()
identity_config.read('../../config/identity.conf')

# Init server obj 
server:Server = Server(
    load_key_pem('../TEST-keys/TEST-public.key', 'public'),
    load_key_pem('../TEST-keys/TEST-private.key', 'private', passphrase='SomeSuperSecurePassphrase'),
    identity_config['IDENTITY']['common_name'],
    network_config['network']['IFACE'],
    5000,
    'peer-info'
)

# Send a multicast hello message using the server
server.send_mcast_hello(
    network_config['multicast']['MCAST_GROUP'],
    int(network_config['multicast']['MCAST_PORT'])
)