from flask import Request
import datetime as dt
import uuid
import secrets
import string


def now() -> str: 
    """Returns the current time as a string for debugging."""
    return dt.datetime.now().strftime('%H:%M:%S')



def get_mac_address() -> str:
    """Returns the device's MAC address in the format "AB:CD:EF:GH:00"."""
    mac = uuid.getnode()
    return ':'.join(f'{(mac >> i) & 0xff:02x}' for i in range(0, 48, 8))


def filter_args(expected_args:dict[str,type], request:Request) -> dict: 
    """Filters the args given in the request to only those in expected_args, adjusts types as appropriate 
    and possible, and returns the result."""
    
    # Get the args given in the request
    given_args:dict[str,str] = {
        a: request.args.get(a, None) 
        for a in expected_args.keys()
    }
            
    # Check the given args types and make sure they are what we expect
    for given_arg, given_val in given_args.items(): 
        
        # If given_val is empty, do nothing 
        if given_val == None or given_val == '': continue
        
        # Convert the value to its expected type if possible
        try:
            # Check int
            if expected_args[given_arg] == int:
                given_args[given_arg] = int(given_val)
            # Check str 
            elif expected_args[given_arg] == str:
                given_args[given_arg] = str(given_val).strip() 
            
         # If conversion fails, ignore this argument   
        except ValueError: given_args[given_arg] = None  
        
        # Given an invalid argument
        except KeyError: given_args[given_arg] = None  
                
    # Fix the "online" arg to be "true" or "false" 
    if given_args.get('online') in (0, 1):  
        given_args['online'] = bool(given_args['online'])
    else:
        given_args['online'] = None 
    
    # Return the adjusted given_args dict
    return given_args


def generate_random_passcode(n:int=20) -> str: 
    """Generates a random alphanumeric passcode of length n."""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(n))