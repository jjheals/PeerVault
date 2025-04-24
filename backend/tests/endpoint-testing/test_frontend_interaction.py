
import pytest
from utils import api_get, api_post

BASE_URL: str = 'http://localhost:8000'

# List of (endpoint, method) pairs
endpoints = [
    ('/ui/get-peer-list', 'GET'),
    ('/ui/get-stored-with-info', 'GET'),
    ('/ui/whoami', 'GET'),
    #('/ui/init-application', 'POST'),
    ('/ui/get-all-info', 'GET'),
    ('/ui/get-storage-info', 'GET'),
    ('/ui/get-user-history', 'GET'),
    ('/ui/get-storage-info', 'GET'),
    ('/ui/get-user-history', 'GET'),
    #('/ui/peer-cn-to-pub-key', 'POST'),
    ('/ui/get-pending-requests', 'GET'),
    #('/ui/upload-data', 'POST'),
    #('/ui/reupload-data', 'POST'),
]

@pytest.mark.parametrize("endpoint,method", endpoints)
def test_api_endpoint(endpoint:str, method:str):
    
    # Act according to the method 
    if method == 'GET': result:bool = api_get(BASE_URL, endpoint)
    elif method == 'POST': result:bool = api_post(BASE_URL, endpoint)
    
    # Fail if unsupported method
    else: pytest.fail(f"Unsupported method: {method}")

    # Assert result (HTTP 200)
    assert result is True, f"API call to {endpoint} with method {method} failed"
