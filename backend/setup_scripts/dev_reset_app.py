
import os 
import requests 
from configparser import ConfigParser
import json 

# Modify sys path to import utils 
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add the parent directory to sys.path
sys.path.insert(0, parent_dir)

from utils import get_mac_address


# ---- Config ---- #
# NOTE: define vars for the configs to pass to signup
PASSPHRASE:str = 'super_secure'
COMMON_NAME:str = 'jjhealey'
PEER_STORAGE_PATH:str = './peer_storage/'       # Relative to backend/
ALLOCATED_STORAGE:float = 50.0

# Define the iface/ip you want (should be real/local network, or loopback)
IFACE:str = '127.0.0.1'

# Load the current identity.conf 
identity_config:ConfigParser = ConfigParser()
identity_config.read('../config/identity.conf')

# Reset the common name and other vars in the identity
identity_config['IDENTITY']['common_name'] = ''
identity_config['IDENTITY']['mac'] = ''
identity_config['IDENTITY']['ip'] = IFACE
identity_config['SETTINGS']['allocated_storage'] = ''
identity_config['PATHS']['peer_storage_path'] = ''

# Rewrite the identity config
with open('../config/identity.conf', 'w+') as file: 
    identity_config.write(file)

# ---- Setup the application ---- #
# NOTE: make sure to hit the signup endpoint instead of just adding the new vars
# to configs because this endpoint creates keys and the DB 
response1:requests.Response = requests.request(
    'POST',
    'http://localhost:8000/ui/signup',
    headers={'Content-Type': 'application/json'},
    data=json.dumps({
        'common_name': COMMON_NAME,
        'passphrase': PASSPHRASE,
        'peer_storage_path': PEER_STORAGE_PATH,
        'allocated_storage': ALLOCATED_STORAGE
    })
)

print('\n\033[93mSIGNUP response: \033[0m\n\n', response1.text)

# ---- Initialize application ---- #
# NOTE: this will start the server
response2:requests.Response = requests.request(
    'POST',
    'http://localhost:8000/ui/init-application/',
    headers={'Content-Type': 'application/json'},
    data=json.dumps({
        'passphrase': PASSPHRASE
    })
)

print('\n\033[93mINIT APP response: \033[0m\n\n', response2.text)