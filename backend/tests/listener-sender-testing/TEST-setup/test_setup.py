
import os 
import sys 
from configparser import ConfigParser
from hashlib import sha256

# Modify path for util imports 
# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

# Add the parent directory to sys.path
sys.path.insert(0, parent_dir)

# Util and object imports
from utils import generate_asymm_keys, gen_aes_key
from objects import DatabaseConnection


# ---- User defined vars ---- # 
# Define a passphrase for the sender and the listener for creating the keys 
SENDER_PASSPHRASE:str = 'i_am_the_sender'
LISTENER_PASSPHRASE:str = 'i_am_the_listener'

# Paths to the config dirs for the sender and listener
# NOTE: these shouldn't ever change
sender_config_dir:str = '../TEST-config/sender/'
listener_config_dir:str = '../TEST-config/listener/'

# Path to the SQL script to create the DB tables
# NOTE: this shouldn't change
SQL_SCRIPT_PATH:str = '../../../sql/create_db_tables.sql'
 
 
# ---- Functions ---- # 
# Define a helper func to make the keygen process simplier
def setup_user_keys(user_passphrase:str, user_enc_config_path:str, user_label:str, rel_save_dir:str='../') -> None: 
    """Creates the keys for the user based on the given passphrase and config file path, and the
    user label is only used for printing updates."""
    
    # Load the config
    user_enc_config:ConfigParser = ConfigParser() 
    user_enc_config.read(user_enc_config_path)
    
    # ---- Creating USER_LABEL keys ---- # 
    # Info print
    print(f'\n\033[94m---- Creating {user_label.upper()} keys ----\033[0m')
    print()
    print(f'{user_label.upper()}_PASSPHRASE: ', user_passphrase)
    print() 

    # Hash the passphrase
    passphrase_hash:str = sha256(user_passphrase.encode()).hexdigest()
    print('Generated passphrase hash (sha256): ', passphrase_hash)

    # Add the passphrase to the enc config 
    user_enc_config['misc']['pass_hash'] = passphrase_hash

    # Resave the enc config with the new passphrase hash 
    with open(user_enc_config_path, 'w') as file: 
        user_enc_config.write(file)

    # Create asymm keys for the user
    print(f'\n\033[93mGenerating asymmetric keys for "{user_label.upper()}"\033[0m')
    print()
    print('PRIV_KEY_PATH: ', user_enc_config['paths']['priv_key_path'])
    print('PUB_KEY_PATH: ', user_enc_config['paths']['pub_key_path'])
    print()

    generate_asymm_keys(
        int(user_enc_config['keys']['size']),
        int(user_enc_config['keys']['exp']),
        os.path.join(rel_save_dir, user_enc_config['paths']['priv_key_path']),
        os.path.join(rel_save_dir, user_enc_config['paths']['pub_key_path']),
        user_passphrase
    )

    # Create a symm key for the user
    print(f'\033[93mGenerating a symmetric key for "{user_label.upper()}"\033[0m')
    print()
    print('SYMM_KEY_PATH: ', user_enc_config['paths']['symm_key_path'])
    print()

    gen_aes_key(
        user_passphrase,
        os.path.join(rel_save_dir, user_enc_config['paths']['symm_key_path'])
    )

    # Done with sender 
    print(f'\033[92mDONE creating "{user_label.upper()}" keys.\033[0m')


# Define a helper func to make the DB creation process simpler 
def setup_user_db(db_path:str, db_log_filepath:str, sql_script_path:str, user_label:str) -> None: 
    """Creates a database at the given db_path using the given SQL script at sql_script_path. The
    user label is only used for info prints."""

    # Info print
    print(f'\n\033[94m---- Creating {user_label.upper()} keys ----\033[0m')
    print()
    print('DB_PATH: ', db_path)
    print('DB_LOG_FILEPATH: ', db_log_filepath)
    print('SQL_SCRIPT_PATH: ', sql_script_path)
    print() 
    
    # NOTE: delete the file if it already exists
    if os.path.exists(db_path): os.remove(db_path)
    
    # --- Create the DB --- # 
    # Init a db connection
    db_connection:DatabaseConnection = DatabaseConnection(
        db_path,
        log_filepath=db_log_filepath  ,
        logger_name=f'{user_label}_db_logger'
    )

    # Execute the sql script
    with open(SQL_SCRIPT_PATH, 'r') as file: 
        # Log
        db_connection.logger.info('Creating tables.')
        db_connection.cursor.executescript(file.read())
    
    # Commit changes 
    db_connection.cxn.commit()

    # Log
    db_connection.logger.info('Successfully created tables.') 

    # Close db connection
    db_connection.cursor.close()
    db_connection.cxn.close()

    # Info print
    print(f'\n\033[92mDONE creating database for "{user_label.upper()}"\033[0m\n')

    
# ---- Setting up the keys for the SENDER and LISTENER users ---- # 
# Call helper for sender
setup_user_keys(
    SENDER_PASSPHRASE,
    os.path.join(sender_config_dir, 'encryption.conf'),
    'sender'
)

# Call helper for listener
setup_user_keys(
    LISTENER_PASSPHRASE,
    os.path.join(listener_config_dir, 'encryption.conf'),
    'listener'
)


# ---- Setting up the database for the SENDER and LISTENER users ---- # 
# Read the flask config to get the DB path and logs dir for both users
sender_flask_config:ConfigParser = ConfigParser() 
sender_flask_config.read(os.path.join(sender_config_dir, 'flask.conf'))

listener_flask_config:ConfigParser = ConfigParser() 
listener_flask_config.read(os.path.join(listener_config_dir, 'flask.conf'))

# Call helper for sender
setup_user_db(
    os.path.join('../', sender_flask_config['paths']['DB_PATH']),
    os.path.join('../', sender_flask_config['paths']['LOGS_DIR'], 'setup-database.log'),
    SQL_SCRIPT_PATH,
    'sender'
)

# Call helper for listener
setup_user_db(
    os.path.join('../', listener_flask_config['paths']['DB_PATH']),
    os.path.join('../', listener_flask_config['paths']['LOGS_DIR'], 'setup-database.log'),
    SQL_SCRIPT_PATH,
    'listener'
)
