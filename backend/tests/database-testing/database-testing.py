
import pytest
import sqlite3 as sql
import os 
import sys
import pandas as pd
from unittest.mock import MagicMock
import random as rand 
import datetime as dt 

# Modify sys path to import utils 
# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the parent directory to sys.path
sys.path.insert(0, parent_dir)

# Object imports
from objects import DatabaseConnection


# ---- Config ---- # 
# Define path to the SQL script to create the DB tables
SQL_SCRIPT:str = '../../sql/create_db_tables.sql'


# ---- Test fixtures ---- #
@pytest.fixture
def db():
    """Creates an in-memory database and executes the CREATE TABLES script."""
    
    # Setup in-memory DB
    cxn:sql.Connection = sql.connect(':memory:')
    cursor:sql.Cursor = cxn.cursor()

    # Create tables
    with open(SQL_SCRIPT, 'r') as file: 
        cursor.executescript(file.read())
        cxn.commit()

    # Patch logger and return DatabaseConnection instance
    mock_logger = MagicMock()
    db_conn = DatabaseConnection(':memory:')
    db_conn.cxn = cxn
    db_conn.cursor = cursor
    db_conn.logger = mock_logger

    yield db_conn

    # Close db connection
    cxn.close()


@pytest.fixture
def peers(db:DatabaseConnection): 
    """Defines a set of peers to create and use for testing."""
    
    sample_peers:list[dict[str, str|bool]] = [
        {'peer_pub_key': 'pub1', 'online': True, 'most_recent_ip': '192.168.1.1', 'common_name': 'Alice', 'mac_last_four': 'ABCD'},
        {'peer_pub_key': 'pub2', 'online': False, 'most_recent_ip': '10.0.0.2', 'common_name': 'Bob', 'mac_last_four': 'EFGH'},
        {'peer_pub_key': 'pub3', 'online': True, 'most_recent_ip': '10.0.0.3', 'common_name': 'Carol', 'mac_last_four': 'IJKL'},
    ]
    
    # Insert each of the peers into the db
    for peer_dict in sample_peers:
        db.new_peer(
            peer_dict['peer_pub_key'],
            peer_dict['online'], 
            peer_dict['most_recent_ip'],
            peer_dict['common_name'],
            peer_dict['mac_last_four']
        )

    # Return the dict
    return sample_peers


@pytest.fixture
def pending_requests(db:DatabaseConnection, peers:list[dict[str, str|bool]]):
    
    # Init vars
    today:str = dt.datetime.now().strftime('%Y-%m-%d')
    directions:list[str] = ['incoming', 'outgoing']
    request_types:list[str] = ['share', 'store', 'retrieve', 'delete']
    file_exts:list[str] = ['txt', 'csv', 'xlsx', 'docx', 'pdf']
    pending_requests:list[dict] = []

    # Create two requests per peer
    i:int = 0
    
    for peer_dict in peers:
        for _ in range(2):  # 2 requests per peer
            
            # Create pseudo-random values
            direction = rand.choice(directions)
            req_type = rand.choice(request_types)
            filename = f'{peer_dict["common_name"]}-file{i}.{rand.choice(file_exts)}'
            size_gb = round(rand.uniform(0.5, 5.0), 2)
            sha256 = f'{peer_dict["common_name"]}-hash-{i}'
            date = today

            # Insert the pending request into the db
            db.new_pending_request(
                direction=direction,
                request_type=req_type,
                peer_pub_key=peer_dict['peer_pub_key'],
                filename=filename,
                size_gb=size_gb,
                sha256=sha256
            )

            # Save info to validate later
            req_id = db.get_request_id(peer_dict['peer_pub_key'], filename, req_type, direction)
            
            pending_requests.append({
                'id': req_id,
                'direction': direction,
                'peer_pub_key': peer_dict['peer_pub_key'],
                'filename': filename,
                'size_gb': size_gb,
                'sha256': sha256,
                'request_type': req_type,
                'request_date': date
            })

    # Return the list of dicts
    return pending_requests


# ---- Test functions ---- # 
def test_peer_exists_and_info_retrieval_bulk(db:DatabaseConnection, peers:list[dict[str, str|bool]]):
    """Tests inserting new peers into the DB and retrieving their info."""
    
    # Create a new peer entry for all the [peers]
    for peer_dict in peers: 
        
        # Retrieve the peer's info from their public key
        info:dict[str, str|bool] = db.peer_info_from_pub_key(peer_dict['peer_pub_key'])
        
        # Assertions for each of the keys
        for key in info.keys(): 
            
            # Check that the peer exists in the DB
            assert db.check_peer_exists(peer_dict['peer_pub_key']) is True
            
            # Handle "online" special since it's boolean
            if key == 'online': 
                assert info[key] == peer_dict[key]
                
            # Handle other keys
            else:             
                assert info[key] == peer_dict[key]
        
    # Test false case
    assert db.check_peer_exists('nonexistent') is False
    
    
def test_pending_requests_inserted_correctly(db:DatabaseConnection, pending_requests:list[dict]):
    """Tests that the [pending_requests] were correctly inserted into the DB by verifying each of the column values."""
    
    # Iterate over the requests
    for req in pending_requests:
        
        # Get the row for this request ID
        row = db.get_pending_request(req['id'])
        
        # Assertions
        assert row is not None                          # Verify we got a result
        assert row['filename'] == req['filename']       # Verify the filename is correct
        assert row['direction'] == req['direction']     # Verify the direction is correct
        assert row['sha256'] == req['sha256']           # Verify the hash is correct


def test_update_and_remove_pending_request(db:DatabaseConnection, pending_requests:list[dict]):
    """Test updating a request's date and then removing it."""
    
    # Pick the first pending request
    req = pending_requests[0]
    new_date = '2024-01-01'
    
    # Update the request date
    db.update_request_date(req['id'], new_date)
    row = db.get_pending_request(req['id'])
    assert row['request_date'] == new_date
    
    # Remove the request
    db.remove_pending_request(req['id'])
    assert db.get_pending_request(req['id']) is None


def test_get_table_columns(db:DatabaseConnection):
    """Tests the get_table_columns() method of DatabaseConnection."""
    
    # Test the Peer table
    columns = db.get_table_columns('Peer')
    
    # Check known col names
    assert 'peer_pub_key' in columns
    assert 'common_name' in columns


def test_get_all_storage_info(db:DatabaseConnection, peers:list[dict[str, str|bool]]):
    """Test summing local, remote, and shared storage using a peer from the fixture."""
    
    # Use the first peer
    peer:dict = peers[0]
    pub_key:str = peer['peer_pub_key']
    
    # Insert new storing with, storing for, and shared entries
    db.new_storing_with_file(pub_key, 'file1.txt', 1.0, 'sha', 'nonce1')
    db.new_storing_for_file(pub_key, 'file2.txt', 2.0, 'sha')
    db.new_shared_file(pub_key, 'incoming', 'file3.txt', 3.0, 'sha')
    
    # Get all the storage info from the DB
    info = db.get_all_storage_info()
    
    # Check that the values are correct
    assert info['gb_storing_with'] == pytest.approx(1.0)
    assert info['gb_storing_for'] == pytest.approx(2.0)
    assert info['gb_shared'] == pytest.approx(3.0)


def test_get_user_history(db:DatabaseConnection, peers:list[dict[str, str|bool]]):
    """Test getting a peer's full file interaction history."""
    
    # Use the second peer (for variety)
    peer:dict = peers[1]
    pub_key:str = peer['peer_pub_key']
    
    # Create new entries in the storing for, storing with, and shared tables
    db.new_storing_for_file(pub_key, 'a.txt', 1.0, 'sha1')
    db.new_storing_with_file(pub_key, 'b.txt', 2.0, 'sha2', 'nonce')
    db.new_shared_file(pub_key, 'outgoing', 'c.txt', 3.0, 'sha3')
    
    # Get the history for this peer
    history = db.get_user_history(pub_key)
    
    # Assertions
    assert len(history['storing_for']) == 1
    assert len(history['storing_with']) == 1
    assert len(history['shared']) == 1


def test_get_storing_with_info(db:DatabaseConnection, peers:list[dict]):
    """Test getting CurrentlyStoringWith records for specific peers or all peers."""
    
    # Use the first and second peers
    pub1:str = peers[0]['peer_pub_key']
    pub2:str = peers[1]['peer_pub_key']
    
    # Create an entry for both these peers
    db.new_storing_with_file(pub1, 'a.txt', 1.0, 'sha1', 'nonce1')
    db.new_storing_with_file(pub2, 'b.txt', 2.0, 'sha2', 'nonce2')
    
    # Get all storing with info and validate the number of entries
    all_df = db.get_storing_with_info([])
    assert len(all_df) == 2
    
    # Check the get_storing_with_info() method for peer 1
    pub1_df:pd.DataFrame = db.get_storing_with_info([pub1])
    
    assert len(pub1_df) == 1                        # Verify only one entry
    assert pub1_df.iloc[0]['peer_pub_key'] == pub1  # Verify the pub key matches


def test_check_stored_file_exists(db:DatabaseConnection, peers:list[dict]):
    """Test checking if a file exists in CurrentlyStoringWith and CurrentlyStoringFor tables."""
    
    # Use the third peer for variety
    pub_key:str = peers[2]['peer_pub_key']
    
    # Create new entries in CurrentlyStoringWith and CurrentlyStoringFor tables for this peer
    db.new_storing_with_file(pub_key, 'file1.txt', 1.0, 'sha', 'nonce')
    db.new_storing_for_file(pub_key, 'file2.txt', 2.0, 'sha')
    
    # Verify results of check_stored_with_file_exists() for this peer
    assert db.check_stored_with_file_exists(pub_key, 'file1.txt') is True           # TRUE case
    assert db.check_stored_with_file_exists(pub_key, 'nonexistent.txt') is False    # FALSE case
    
    # Verify results of check_stored_for_file_exists() for this peer
    assert db.check_stored_for_file_exists(pub_key, 'file2.txt') is True            # TRUE case
    assert db.check_stored_for_file_exists(pub_key, 'nonexistent.txt') is False     # FALSE case


def test_get_used_storage(db:DatabaseConnection, peers:list[dict]):
    """Test summing storage values for local and remote usage."""
    
    # Use the second and third peers
    pub1:str = peers[1]['peer_pub_key']
    pub2:str = peers[2]['peer_pub_key']
    
    # Create new entries in storing with and storing for for both peers
    db.new_storing_with_file(pub1, 'fileA.txt', 3.0, 'shaA', 'nonce')
    db.new_storing_with_file(pub1, 'fileB.txt', 2.3, 'shaB', 'nonce')
    db.new_storing_for_file(pub1, 'fileC.txt', 5.0, 'shaC')
    
    db.new_storing_with_file(pub2, 'fileD.txt', 1.0, 'shaD', 'nonce')
    db.new_storing_with_file(pub2, 'fileE.txt', 2.0, 'shaE', 'nonce')
    db.new_storing_for_file(pub2, 'fileF.txt', 1.2, 'shaF')
    
    # Check that the storage sums are correct (when filtering on pub key 1)
    assert db.get_remote_used_storage(pub1) == pytest.approx(5.3)
    assert db.get_local_used_storage(pub1) == pytest.approx(5.0)

    # Check that the storage sums are correct (when not filtering on pub key)
    assert db.get_remote_used_storage() == pytest.approx(8.3)
    assert db.get_local_used_storage() == pytest.approx(6.2)


def test_get_stored_file_nonce(db:DatabaseConnection, peers:list[dict]):
    """Test retrieving the base64 nonce for a stored file."""
    
    # Use the third peer
    pub_key:str = peers[2]['peer_pub_key']
    
    # Create a new entry in CurrentlyStoringWith for this peer
    db.new_storing_with_file(pub_key, 'secured.txt', 1.2, 'securehash', 'base64nonce')
    
    # Assertions
    assert db.get_stored_file_nonce(pub_key, 'secured.txt') == 'base64nonce'    # TRUE case
    assert db.get_stored_file_nonce(pub_key, 'missing.txt') is None             # FALSE case


def test_get_matching_peers(db:DatabaseConnection, peers:list[dict]):
    """Test filtering peers based on one or more attributes."""
    
    # Use the first peer
    pub_key:str = peers[0]['peer_pub_key']
    
    # Match by common name
    df:pd.DataFrame = db.get_matching_peers(common_name='Alice')
    
    assert not df.empty                             # Verify we got results
    assert len(df) == 1                             # Verify number of results
    assert df.iloc[0]['peer_pub_key'] == pub_key    # Verify that the pub key matches
    
    # Match by online + IP
    df2:pd.DataFrame = db.get_matching_peers(online=True, most_recent_ip='192.168.1.1')
    
    assert not df.empty                             # Verify we got results
    assert len(df2) == 1                            # Verify number of results
    assert df2.iloc[0]['common_name'] == 'Alice'    # Verify that the common name matches
    

def test_pub_key_cn_mapping(db:DatabaseConnection, peers:list[dict]):
    """Test common name <-> public key mapping."""
    
    # Use the first peer
    peer:dict = peers[0]
    
    # Check pub_key -> common_name map
    cn:str = db.cn_from_pub_key(peer['peer_pub_key'])
    assert cn == peer['common_name']
    
    # Check common_name -> pub_key map
    keys:list[str] = db.pub_key_from_cn(peer['common_name'])
    
    assert len(keys) == 1                   # Verify number of results
    assert peer['peer_pub_key'] in keys     # Verify that the match is correct

