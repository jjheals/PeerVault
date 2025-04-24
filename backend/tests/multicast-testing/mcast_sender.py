import os 
from configparser import ConfigParser

# Modify sys path to import utils 
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the parent directory to sys.path
sys.path.insert(0, parent_dir)

# Util and object imports
from utils import load_key_pem
from objects import Server, DatabaseConnection


# --- Config --- #
# Network config
network_config:ConfigParser = ConfigParser()
network_config.read('../../config/network.conf')

MCAST_GRP = network_config['multicast']['MCAST_GROUP']       # Multicast group addr
MCAST_PORT = int(network_config['multicast']['MCAST_PORT'])  # Port to listen on
IFACE = network_config['multicast']['LOCAL_IP']              # Local IP
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

# NOTE: defining other static paths for testing 
DB_PATH:str = '../TEST-data/TEST-database.db'
DB_LOG_PATH:str = '../TEST-logs/TEST-database.log'
SERVER_LOG_PATH:str = '../TEST-logs/TEST-server.log'
PEER_STORAGE_DIR:str = '../TEST-peer-storage/'

# --- Init --- #
# Init a Server obj
server:Server = Server(
    PUBLIC_KEY_PEM,         # pub_key_pem
    PRIV_KEY_PEM,           # priv_key_pem
    '',                     # symm_aes_key - NOTE: symm AES key doesn't matter for this test script
    COMMON_NAME,            # common_name
    IFACE,                  # iface
    PORT,                   # port
    IFACE,                  # mcast_iface
    MCAST_PORT,             # mcast_port
    MCAST_GRP,              # mcast_group
    DatabaseConnection(DB_PATH, DB_LOG_PATH),  # db_connection
    PEER_STORAGE_DIR,                          # peer_storage_dir
    log_filepath=SERVER_LOG_PATH               # log_filepath
)


# --- Multicast send --- #
server.send_mcast_hello()