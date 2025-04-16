from flask import Request
import datetime as dt
import uuid
import secrets
import string 
from hashlib import sha256
import os
from io import BytesIO
import socket


def now() -> str: 
    """Returns the current time as a string for debugging."""
    return dt.datetime.now().strftime('%H:%M:%S')


def hash_bytes_sha256(byte_data:bytes) -> str:
    """Takes in a bytes object and hashes it using sha256."""

    # Init hash 
    sha256_hash = sha256()

    # Wrap the byte data in file-like object
    byte_stream = BytesIO(byte_data)  

    for byte_block in iter(lambda: byte_stream.read(4096), b""):
        sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def hash_str_sha256(s:str) -> str: 
    """Takes in a str obj and hashes it using sha256."""
    return sha256(s).hexdigest()


def get_mac_address() -> str:
    """Returns the device's MAC address in the format "AB:CD:EF:GH:00"."""
    mac = uuid.getnode()
    return ':'.join(f'{(mac >> i) & 0xff:02x}' for i in range(0, 48, 8))

def get_IP_address() -> str:
    """Returns the device's MAC address in the format "AB:CD:EF:GH:00"."""
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address


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


def write_to_file(filename:str, content:bytes) -> str:
    """Writes content to a file.

        Parameters:
            filename (str): The name of the file to write to.
            content (str): The content to be written to the file.

        Returns a string: 
            "File written": no errors in the method
            "File already exists": did not save the file as it is already is storeage
            "Error occured": There was a unexpected error and logs will need to be checked  
    """
    try:
        # Check if the file already exists
        if os.path.exists(filename):
            raise FileExistsError(f"File '{filename}' already exists.")
        
        # Write content to the file
        with open(filename, 'wb') as file:
            file.write(content)
        
        # Return success
        return "File written"
    
    # Log a warning if the file already exists
    except FileExistsError as e: 
        print('\033[91mERROR in write_to_file(): \033[0mFile already exists.')
        return "File already exists"
    
        # Log any other exceptions that occur
    except Exception as e: 
        print('\033[91mERROR in write_to_file(): \033[0m', e)
        return "Error occured"
    

def bytes_to_gb(num_bytes:int|float) -> float:
    """Takes in a number of bytes and converts to GB"""
    return num_bytes / (1024 ** 3)