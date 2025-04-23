import os 
from configparser import ConfigParser

# Modify sys path to import utils 
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the parent directory to sys.path
sys.path.insert(0, parent_dir)

# Util and object imports
from utils import load_key_pem, load_aes_key
from objects import Server


# --- Config --- #
# Network config
network_config:ConfigParser = ConfigParser()
network_config.read('../../config/network.conf')

MCAST_GRP = network_config['multicast']['MCAST_GROUP']       # Multicast group addr
MCAST_PORT = int(network_config['multicast']['MCAST_PORT'])  # Port to listen on
IFACE = "127.0.0.1" #network_config['multicast']['LOCAL_IP']              # Local IP
PORT = int(network_config['network']['PORT'])

# Identity config
identity_config:ConfigParser = ConfigParser()
identity_config.read('../../config/identity.conf')

COMMON_NAME:str = identity_config['IDENTITY']['common_name']    # Common name

# Encryption config 
# NOTE: using static paths relative to this script rather than the paths in enc config
#enc_config:ConfigParser = ConfigParser()
#enc_config.read('../../config/encryption.conf')

PUBLIC_KEY_PEM:str = load_key_pem('../TEST-keys/TEST-public.key', 'public')
PRIV_KEY_PEM:str = load_key_pem('../TEST-keys/TEST-private.key', 'private', 'SomeSuperSecurePassphrase')

SYMM_KEY:str = load_aes_key('SomeSuperSecurePassphrase', '../TEST-keys/TEST-symm.key')

# --- Init --- #
# Init a Server obj
server:Server = Server(
    PUBLIC_KEY_PEM,         # pub_key_pem
    PRIV_KEY_PEM,           # priv_key_pem
    SYMM_KEY,               # symm_aes_key
    COMMON_NAME,            # common_name
    IFACE,                  # iface
    PORT,                   # port
    IFACE,                  # mcast_iface
    MCAST_PORT,             # mcast_port
    MCAST_GRP,              # mcast_group
<<<<<<< HEAD
    '../../peer-info/',      # data_dir_path
    '/home/quentin-hall/Desktop/Capstone/delete_request/test-data'  # peer_storage_path

=======
    '../../peer-info/',     # data_dir_path
    identity_config['PATHS']['peer_storage_path']   # peer_storage_dir
>>>>>>> f5ad5484f9a4c4145745e094d26be51dc3b8435a
)



# --- Send a file --- #
# Get the target IP address from CLI
target_ip:str = input('\033[93mEnter the target IPv4 address: \033[0m')

# Send the request
server.send_delete_request(
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxXaJgt8rIUYgt56X1Zb/YIKIeLQ+jBN2gxWo1PzYVXKTH/zBdwXL7SA0LJ6WVfQSG8RIHDMul7TQgOB6dI25S8JhkIurT44lIKSgK9XfUnX11ZTp9gA/UeYiL5+UQrCgn3D2sYiXXFsUzaWel9JdE1U5wtiajNG/19z+Ltu8mk+L6cW32qHsI9+6aV6TgKKLT1Q/nmj/ldeTPL/4fsgp9msL40/5cJjnAYMlidtxRZpJQgFjGN660s/TYMvyf8N0DXSfEaVIySNvFry7NshybLySKsYXzaHTKN7uiVjDG0B435gkUP90gsh4a85fd5UY5doRCyI2NGgWqNXh02ze9wIDAQAB",
    target_ip,
<<<<<<< HEAD
    'test.txt',
    '39f7739d82141c0229604ad917edfee0d1a258fbb1face62589cd6914b8226e4'
)

=======
    'test.txt'
)
>>>>>>> f5ad5484f9a4c4145745e094d26be51dc3b8435a
