import os 
from configparser import ConfigParser 

# Modify sys path to import utils 
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add the parent directory to sys.path
sys.path.insert(0, parent_dir)

# Other imports 
from objects import DatabaseConnection
from utils import now


def main(): 
    
    # --- Setup --- #
    # Define the path to the SQL script to create the tables
    SQL_SCRIPT_PATH:str = 'sql/create_db_tables.sql'

    # Read the flask config to get the DB path and logs dir
    config:ConfigParser = ConfigParser() 
    config.read('config/flask.conf')

    # Extract the config vars 
    # NOTE: combine paths with parent dir so that the files are created relative to the backend/ dir, not the setup-scripts/ dir
    DB_PATH:str = os.path.join(parent_dir, config['paths']['DB_PATH'])
    LOGS_DIR:str = os.path.join(parent_dir, config['paths']['LOGS_DIR'])


    # --- Create the DB --- # 
    print(f'\n\033[0m[{now()}] \033[93mCreating database at "{DB_PATH}"\033[0m')

    # Remove the current DB if it exists
    if os.path.exists(DB_PATH): os.remove(DB_PATH)

    # Init a db connection
    db_connection:DatabaseConnection = DatabaseConnection(
        DB_PATH,
        log_filepath=os.path.join(LOGS_DIR, 'setup-database.log')    
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
    print(f'\n\033[0m[{now()}] \033[92mDatabase created successfully.\033[0m\n')


# CALL 
main()