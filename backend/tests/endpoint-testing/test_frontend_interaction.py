
import pytest
import os 
import sys
import sqlite3 as sql

from utils import api_get, api_post

# Modify sys path to import utils 
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, parent_dir)

# Util and object imports
from objects import DatabaseConnection


# ---- Config ---- #
# Define global vars
BASE_URL:str = 'http://localhost:8000'    # Base URL of the API 
PASSPHRASE:str = 'super_secure'           # Passphrase to pass to /ui/init-application/

# List of (endpoint, method) pairs
endpoints = [
    ('/ui/get-peer-list', 'GET', {}),
    ('/ui/get-stored-with-info', 'GET', {}),
    ('/ui/whoami', 'GET', {}),
    ('/ui/init-application', 'POST', {'passphrase': PASSPHRASE}),
    ('/ui/get-all-info', 'GET', {}),
    ('/ui/get-storage-info', 'GET', {}),
    ('/ui/get-user-history', 'GET', {}),
    ('/ui/get-storage-info', 'GET', {}),
    ('/ui/get-user-history', 'GET', {}),
    #('/ui/peer-cn-to-pub-key', 'POST', {}),
    ('/ui/get-pending-requests', 'GET', {}),
    #('/ui/upload-data', 'POST', {}),
    #('/ui/reupload-data', 'POST', {}),
]

# Parametreize endpoints
@pytest.mark.parametrize("endpoint,method,args", endpoints)


# ---- Functions ---- #

def test_api_endpoint(endpoint:str, method:str, args:dict):
    
    # Act according to the method 
    # GET request
    if method == 'GET': 
        result:bool = api_get(
            BASE_URL, 
            endpoint, 
            args=args
        )
        
    # POST request
    elif method == 'POST': 
        result:bool = api_post(
            BASE_URL, 
            endpoint,
            body=args
        )
    
    # Fail if unsupported method
    else: pytest.fail(f"Unsupported method: {method}")

    # Assert result (HTTP 200)
    assert result is True, f"API call to {endpoint} with method {method} failed"
