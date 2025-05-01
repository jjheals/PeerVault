import os 
from configparser import ConfigParser

# Modify sys path to import utils 
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the parent directory to sys.path
sys.path.insert(0, parent_dir)

# Util and object imports
from utils import load_key_pem, load_aes_key, load_configs
from objects import Server, DatabaseConnection


# --- Config --- #
# NOTE: loading info for the SENDER 
# NOTE: define the passphrase for loading the keys
PASSPHRASE:str = 'i_am_the_sender'

# Load the configs
config_parsers:dict[str, ConfigParser] = load_configs('TEST-config/sender/')

# Extract vars from network config
network_config:ConfigParser = config_parsers['network']

MCAST_GRP = network_config['multicast']['MCAST_GROUP']       # Multicast group addr
MCAST_PORT = int(network_config['multicast']['MCAST_PORT'])  # Port to listen on
IFACE = network_config['multicast']['LOCAL_IP']              # Local IP
PORT = int(network_config['network']['PORT'])                # Server port

# Extract vars from identity config
identity_config:ConfigParser = config_parsers['identity']

COMMON_NAME:str = identity_config['IDENTITY']['common_name']            # Common name
PEER_STORAGE_DIR:str = identity_config['PATHS']['peer_storage_path']    # Peer storage path

# Extract vars from encryption config 
enc_config:ConfigParser = config_parsers['encryption']

PUBLIC_KEY_PEM:str = load_key_pem(enc_config['paths']['pub_key_path'], 'public')
PRIV_KEY_PEM:str = load_key_pem(enc_config['paths']['priv_key_path'], 'private', PASSPHRASE)
SYMM_KEY:str = load_aes_key(PASSPHRASE, enc_config['paths']['symm_key_path'])

# Extract vars from flask config
flask_config:ConfigParser = config_parsers['flask']

LOGS_DIR:str = flask_config['paths']['LOGS_DIR']    # Path to the dir to output logs
DB_PATH:str = flask_config['paths']['DB_PATH']      # Path to the test DB

# Construct rel paths from the vars from flask config
DB_LOG_PATH:str = os.path.join(LOGS_DIR, 'share', 'sender-database.log')     # Path to output DB logs
SERVER_LOG_PATH:str = os.path.join(LOGS_DIR, 'share', 'sender-server.log')   # Path to output server logs

# Create unique names for the loggers so they don't interfere with other scripts
SERVER_LOGGER_NAME:str = 'share_sender_server_logger'  # Name for the server logger
DB_LOGGER_NAME:str = 'share_sender_db_logger'          # Name for the DB logger      


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
    DatabaseConnection(     # send_db_connection
        DB_PATH, 
        DB_LOG_PATH, 
        logger_name=DB_LOGGER_NAME
    ),
    DB_PATH,                            # db_filepath
    PEER_STORAGE_DIR,                   # peer_storage_dir
    log_filepath=SERVER_LOG_PATH,       # log_filepath
    logger_name=SERVER_LOGGER_NAME,     # logger_name
    db_log_filepath=DB_LOG_PATH,        # db_log_filepath
    db_logger_name=DB_LOGGER_NAME,      # db_logger_name
    temp_dir='.tmp/sender/'
)

# --- Multicast send --- #
server.send_mcast_hello()