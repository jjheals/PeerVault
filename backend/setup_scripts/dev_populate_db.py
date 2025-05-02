
import os
import random
from datetime import datetime, timedelta
from configparser import ConfigParser
from tqdm import tqdm 
import pandas as pd
from tabulate import tabulate 

# Modify sys path to import utils 
import sys

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

# Other imports 
from objects import DatabaseConnection
from utils import now


# --- Config --- #
# Read the flask config to get the DB path and logs dir
config:ConfigParser = ConfigParser() 
config.read('../config/flask.conf')

# Extract the config vars 
# NOTE: combine paths with parent dir so that the files are created relative to the backend/ dir, not the setup-scripts/ dir
DB_PATH:str = os.path.join(parent_dir, config['paths']['DB_PATH'])
LOGS_DIR:str = os.path.join(parent_dir, config['paths']['LOGS_DIR'])

# Define the path to the SQL script to create the tables
SQL_SCRIPT_PATH:str = '../sql/create_db_tables.sql'


# --- Helper funcs --- #
def random_date(start_year:int=2023, end_year:int=2025) -> str:
    """Generates a random date between the given start and end year and returns a string in YYYY-MM-DD format."""
    
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end - start).days))).strftime('%Y-%m-%d')


# --- Define dummy data for each table --- #

# Peer
peer_data:list[dict] = [
    {"peer_pub_key": "peerkey1", "online": True, "most_recent_ip": "192.168.1.1", "common_name": "Alice", "mac_last_four": "A1B2"},
    {"peer_pub_key": "peerkey2", "online": False, "most_recent_ip": "10.0.0.2", "common_name": "Bob", "mac_last_four": "C3D4"},
    {"peer_pub_key": "peerkey3", "online": True, "most_recent_ip": "172.16.0.3", "common_name": "Charlie", "mac_last_four": "E5F6"},
    {"peer_pub_key": "peerkey4", "online": True, "most_recent_ip": "192.168.1.4", "common_name": "Dana", "mac_last_four": "G7H8"},
    {"peer_pub_key": "peerkey5", "online": False, "most_recent_ip": "10.0.0.5", "common_name": "Eve", "mac_last_four": "I9J0"},
    {"peer_pub_key": "peerkey6", "online": True, "most_recent_ip": "192.168.2.6", "common_name": "Frank", "mac_last_four": "K1L2"},
    {"peer_pub_key": "peerkey7", "online": False, "most_recent_ip": "10.1.1.7", "common_name": "Grace", "mac_last_four": "M3N4"}
]

# CurrentlyStoringFor
currently_storing_for_data:list[dict] = [
    {"peer_pub_key": "peerkey1", "filename": "document1.pdf", "size_gb": 1.2, "sha256": "dummysha256hash1", "store_date": random_date()},
    {"peer_pub_key": "peerkey2", "filename": "photo_album.zip", "size_gb": 2.5, "sha256": "dummysha256hash2", "store_date": random_date()},
    {"peer_pub_key": "peerkey3", "filename": "notes.txt", "size_gb": 0.3, "sha256": "dummysha256hash8", "store_date": random_date()},
    {"peer_pub_key": "peerkey4", "filename": "presentation.pptx", "size_gb": 1.7, "sha256": "dummysha256hash9", "store_date": random_date()},
    {"peer_pub_key": "peerkey5", "filename": "design.psd", "size_gb": 4.8, "sha256": "dummysha256hash10", "store_date": random_date()},
    {"peer_pub_key": "peerkey6", "filename": "finance_report.xlsx", "size_gb": 0.9, "sha256": "dummysha256hash18", "store_date": random_date()},
    {"peer_pub_key": "peerkey7", "filename": "music_collection.zip", "size_gb": 12.0, "sha256": "dummysha256hash19", "store_date": random_date()}
]

# CurrentlyStoringWith
currently_storing_with_data:list[dict] = [
    {"peer_pub_key": "peerkey1", "filename": "backup_data.tar", "size_gb": 5.0, "sha256": "dummysha256hash3", "b64_nonce": "dummyb64nonce1", "store_date": random_date()},
    {"peer_pub_key": "peerkey3", "filename": "db_backup.sql", "size_gb": 6.2, "sha256": "dummysha256hash11", "b64_nonce": "dummyb64nonce2", "store_date": random_date()},
    {"peer_pub_key": "peerkey4", "filename": "machine_learning_model.pkl", "size_gb": 2.9, "sha256": "dummysha256hash12", "b64_nonce": "dummyb64nonce3", "store_date": random_date()},
    {"peer_pub_key": "peerkey6", "filename": "system_image.img", "size_gb": 15.5, "sha256": "dummysha256hash20", "b64_nonce": "dummyb64nonce4", "store_date": random_date()}
]

# PreviouslySharedWith
previously_shared_with_data:list[dict] = [
    {"peer_pub_key": "peerkey1", "direction": "outgoing", "filename": "shared_doc.docx", "size_gb": 0.5, "sha256": "dummysha256hash4", "share_date": random_date()},
    {"peer_pub_key": "peerkey2", "direction": "incoming", "filename": "received_video.mp4", "size_gb": 10.0, "sha256": "dummysha256hash5", "share_date": random_date()},
    {"peer_pub_key": "peerkey3", "direction": "outgoing", "filename": "sketch.png", "size_gb": 0.2, "sha256": "dummysha256hash13", "share_date": random_date()},
    {"peer_pub_key": "peerkey4", "direction": "incoming", "filename": "thesis.pdf", "size_gb": 1.5, "sha256": "dummysha256hash14", "share_date": random_date()},
    {"peer_pub_key": "peerkey5", "direction": "outgoing", "filename": "soundtrack.mp3", "size_gb": 0.9, "sha256": "dummysha256hash15", "share_date": random_date()},
    {"peer_pub_key": "peerkey6", "direction": "incoming", "filename": "manual.docx", "size_gb": 2.2, "sha256": "dummysha256hash21", "share_date": random_date()},
    {"peer_pub_key": "peerkey7", "direction": "outgoing", "filename": "poster.pdf", "size_gb": 1.0, "sha256": "dummysha256hash22", "share_date": random_date()}
]

# PendingRequests
pending_requests_data:list[dict] = [
    # NOTE: the first two entries will be moved to "CompletedRequests"
    {"direction": "incoming", "request_type": "store", "peer_pub_key": "peerkey1", "filename": "pending_file.dat", "size_gb": 3.4, "sha256": "dummysha256hash6", "accepted": True, "request_date": random_date()},
    {"direction": "outgoing", "request_type": "share", "peer_pub_key": "peerkey3", "filename": "music_playlist.m3u", "size_gb": 0.1, "sha256": "dummysha256hash16", "accepted": False, "request_date": random_date()},
    {"direction": "incoming", "request_type": "delete", "peer_pub_key": "peerkey5", "filename": "old_project.zip", "size_gb": 7.6, "sha256": "dummysha256hash17", "accepted": None, "request_date": random_date()},
    {"direction": "outgoing", "request_type": "store", "peer_pub_key": "peerkey6", "filename": "upload_new.iso", "size_gb": 2.4, "sha256": "dummysha256hash23", "accepted": None, "request_date": random_date()},
    {"direction": "incoming", "request_type": "retrieve", "peer_pub_key": "peerkey7", "filename": "request_old_backup.bak", "size_gb": 14.7, "sha256": "dummysha256hash24", "accepted": None, "request_date": random_date()}
]

# --- Init DB --- #
# Check if the DB path exists BEFORE init-ing DatabaseConnection
db_exists:bool = os.path.exists(DB_PATH)

# Init a db connection
db_connection:DatabaseConnection = DatabaseConnection(
    DB_PATH,
    log_filepath=os.path.join(LOGS_DIR, 'setup-database.log')    
)

# If the DB didn't exist yet, create the tables
if not os.path.exists(DB_PATH): 
    print(f'\n\033[0m[{now()}] \033[93mCreating database at "{DB_PATH}"\033[0m')
    
    # Execute the sql script
    with open(SQL_SCRIPT_PATH, 'r') as file: 
        db_connection.logger.info('Creating tables.')
        db_connection.cursor.executescript(file.read())
        
    # Commit changes and log
    db_connection.cxn.commit()
    db_connection.logger.info('Successfully created tables.') 

# DB already existed, so we don't need to create the tables
else:  
    print(f'\n\033[0m[{now()}] \033[93mConnecting to existing database at "{DB_PATH}"\033[0m')


# --- Populate the tables --- #
print()

# 1. Peer
for peer_dict in tqdm(peer_data, total=len(peer_data), desc='Populating "Peer" table'): 
    db_connection.new_peer(
        peer_dict['peer_pub_key'],
        peer_dict['online'],
        peer_dict['most_recent_ip'],
        peer_dict['common_name'],
        peer_dict['mac_last_four']
    )
    
# 2. CurrentlyStoringFor
for d in tqdm(currently_storing_for_data, total=len(currently_storing_for_data), desc='Populating "CurrentlyStoringFor" table'):
    db_connection.new_storing_for_file(
        d['peer_pub_key'],
        d['filename'],
        d['size_gb'], 
        d['sha256'],
        store_date=d['store_date']
    )
    
# 3. CurrentlyStoringWith 
for d in tqdm(currently_storing_with_data, total=len(currently_storing_with_data), desc='Populating "CurrentlyStoringWith" table'): 
    db_connection.new_storing_with_file(
        d['peer_pub_key'],
        d['filename'],
        d['size_gb'],
        d['sha256'],
        d['b64_nonce'],
        store_date=d['store_date']
    )

# 4. PreviouslySharedWith
for d in tqdm(previously_shared_with_data, total=len(previously_shared_with_data), desc='Populating "PreviouslySharedWith" table'):
    db_connection.new_shared_file(
        d['peer_pub_key'],
        d['direction'],
        d['filename'],
        d['size_gb'],
        d['sha256'],
        share_date=d['share_date']
    )

# 5. PendingRequests
for d in tqdm(pending_requests_data, total=len(pending_requests_data), desc='Populating "PendingRequests" table'):
    db_connection.new_pending_request(
        d['direction'],
        d['request_type'], 
        d['peer_pub_key'],
        d['filename'], 
        d['size_gb'],
        d['sha256'], 
        accepted=d['accepted'],
        request_date=d['request_date']
    )
    
# 6. CompletedRequests
# NOTE: for this one, just move 2-3 PendingRequests into the CompletedRequets table
for i in tqdm(range(0,3), total=3, desc='Populating "CompletedRequests" table'):    
    db_connection.completed_pending_request(i) # Request ID "1"

# Info print
print(f'\n\033[0m[{now()}] \033[92mDone inserting dummy data.\033[0m')


# --- Validate --- #
# For each table, print info about the new values
print()
for table_name in ['Peer', 'CurrentlyStoringFor', 'CurrentlyStoringWith', 'PreviouslySharedWith', 'PendingRequests', 'CompletedRequests']:
    
    # Get the table as a df
    df:pd.DataFrame = db_connection.table_as_df(table_name)
    
    # Print info about this table 
    print(f'\033[94m--------------- [{table_name}] ---------------\033[0m')
    print(f'Number of rows: {len(df)}\n')
    print(f'Head: \n')
    print(tabulate(df.head(), headers='keys', tablefmt='grid'))
    print()
    
    
