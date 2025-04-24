# test_database_connection.py

import pytest
import sqlite3 as sql
import os 
import sys
import pandas as pd
from unittest.mock import MagicMock

# Modify sys path to import utils 
# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the parent directory to sys.path
sys.path.insert(0, parent_dir)

# Object imports
from objects import DatabaseConnection


# ---- Config ---- # 
SQL_SCRIPT:str = '../../sql/create_db_tables.sql'

@pytest.fixture
def db():
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


def test_new_peer_and_retrieval(db:DatabaseConnection):
    db.new_peer('pub1', True, '192.168.1.1', 'Alice', 'ABCD')
    info = db.peer_info_from_pub_key('pub1')
    assert info['common_name'] == 'Alice'


def test_check_peer_exists(db:DatabaseConnection):
    db.new_peer('pub2', False, '192.168.1.2', 'Bob', 'EFGH')
    assert db.check_peer_exists('pub2') is True
    assert db.check_peer_exists('nonexistent') is False


def test_new_pending_request_and_get_id(db:DatabaseConnection):
    db.new_peer('pub3', True, '10.0.0.1', 'Carol', 'IJKL')
    db.new_pending_request('incoming', 'store', 'pub3', 'file1.txt', 1.23, 'hash123')
    req_id = db.get_request_id('pub3', 'file1.txt', 'incoming')
    assert req_id != -1


def test_update_and_remove_pending_request(db:DatabaseConnection):
    db.new_peer('pub4', True, '10.0.0.2', 'Dave', 'MNOP')
    db.new_pending_request('outgoing', 'share', 'pub4', 'file2.txt', 2.34, 'hash456')
    req_id = db.get_request_id('pub4', 'file2.txt', 'outgoing')
    db.update_request_date(req_id, '2024-01-01')
    row = db.get_pending_request(req_id)
    assert row['request_date'] == '2024-01-01'
    db.remove_pending_request(req_id)
    assert db.get_pending_request(req_id) is None


def test_get_table_columns(db:DatabaseConnection):
    columns = db.get_table_columns('Peer')
    assert 'peer_pub_key' in columns
    assert 'common_name' in columns


def test_get_all_storage_info(db:DatabaseConnection):
    db.new_peer('pub5', True, '10.0.0.3', 'Eve', 'QRST')
    db.new_storing_with_file('pub5', 'file.txt', 1.0, 'hash', 'nonce')
    db.new_storing_for_file('pub5', 'file.txt', 2.0, 'hash')
    db.new_shared_file('pub5', 'incoming', 'file.txt', 3.0, 'hash')
    info = db.get_all_storage_info()
    assert info['gb_storing_with'] == 1.0
    assert info['gb_storing_for'] == 2.0
    assert info['gb_shared'] == 3.0


def test_get_user_history(db:DatabaseConnection):
    db.new_peer('pub6', True, '10.0.0.4', 'Frank', 'UVWX')
    db.new_storing_for_file('pub6', 'a.txt', 1.0, 'sha')
    db.new_storing_with_file('pub6', 'b.txt', 2.0, 'sha', 'nonce')
    db.new_shared_file('pub6', 'incoming', 'c.txt', 3.0, 'sha')
    history = db.get_user_history('pub6')
    assert len(history['storing_for']) == 1
    assert len(history['storing_with']) == 1
    assert len(history['shared']) == 1
