
import requests
import json 


def api_post(url:str, endpoint:str, body:dict={}) -> bool:
    """Makes an API POST request to the given endpoint at the given URL with the given body."""
    
    try: 
        # Make API request
        response:requests.Response = requests.post(
            f'{url.rstrip("/")}/{endpoint.lstrip('/')}',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(body)
        )

        # Print response
        print('\033[0mPOST Request: \033[0m')
        print(f'\tURL: {url}')
        print(f'\tEndpoint: {endpoint}')
        print(f'\tBody: {body}')
        
        print(f'\nRESPONSE: ')
        print(f'\tStatus: {response.status_code}')
        print(f'\tText: {response.text}')
        
        # Handle response 
        if response.status_code == 200: 
            print('\033[92mSUCCESS.\033[0m\n')
            return True        
        else: 
            print(f'\033[91mERROR.\033[0m\n')
            return False
        
    # Handle exceptions: 
    except Exception as e: 
        print(f'\033[91mERROR in api_post(): \033[0m{e.__class__} - {e}')
        return False
    
    
def api_get(url:str, endpoint:str, args:dict={}) -> bool:
    """Makes an API POST request to the given endpoint at the given URL with the given body."""
    
    # Construct string for the arguments 
    args_str:str = ""
    for k,v in args.items(): args_str += f"{k}={v}&"
    
    try: 
        # Make API request
        response:requests.Response = requests.get(
            f'{url.rstrip("/")}/{endpoint.lstrip('/')}/?' + args_str,
            headers={'Content-Type': 'application/json'}
        )

        # Print response
        print('\033[0mGET Request: \033[0m')
        print(f'\tURL: {url}')
        print(f'\tEndpoint: {endpoint}')
        print(f'\tArgs: {args}')
        
        print(f'\nRESPONSE: ')
        print(f'\tStatus: {response.status_code}')
        print(f'\tText: {response.text}')
        
        # Handle response 
        if response.status_code == 200: 
            print('\033[92mSUCCESS.\033[0m\n')
            return True        
        else: 
            print(f'\033[91mERROR.\033[0m\n')
            return False
        
    # Handle exceptions: 
    except Exception as e: 
        print(f'\033[91mERROR in api_get(): \033[0m{e.__class__} - {e}')
        return False