
from flask import Blueprint, jsonify, g, current_app, request, abort
import json 
import os 
import pandas as pd
from configparser import ConfigParser

from utils import filter_args, load_key, get_mac_address
from .funcs import require_localhost

# ---- Config & init ---- #
# Create blueprint
fi_bp:Blueprint = Blueprint('frontend_interaction', __name__)


# ---- Add endpoints ---- #
@fi_bp.route('/ui/get-peer-list', methods=['GET'])
@require_localhost
def get_peer_list(): 
    ''' 
        DESC: endpoint to get the current state of the peer list CSV file.
        
        ARGS: 
            
            online (int<0|1>) - filter by if the peers are active or not
            friended (str<Y,N,W>) - filter by the status of friended from peers 
            peer_pub_key (str) - filter by public key
            most_recent_ip (str) - filter by the most recently known IP for peers
            common_name (str) - filter by common name 
            mac_last_four (str) - filter by the last four of the MAC for peers
            
            NOTE: 
                - all args are optional
                - all args are filtered to exact matches 
                - all given args are applied as AND clauses, i.e. only peers that match all given args will be 
                  returned. If an arg is not given or is null/None/empty, that filter is not applied, and args that 
                  do not match the expected type will be ignored
                  
        RETURNS: 
            
            - 200 | successful: (dict) an array JSON object where each value is a dictionary containing the information for a single
            peer, and where the returned values match the given criteria.
            - 400 | bad request: if the client supplies an unsupported method or some other error in the client's request.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | server error: if some unexpected error occurs during server-side processing of the request.
    '''
    
    # Define expected args for easy checks of given args and their types
    expected_args:dict = {
        'online': int,
        'common_name': str,
        'peer_pub_key': str,
        'friended': str,
        'most_recent_ip': str,
        'mac_last_four': str
    }        

    # Filter the request's args to just those that match the formats in expected_args
    given_args:dict = filter_args(expected_args, request)

    # Read the current all-peers.csv file as a df
    all_peers_df:pd.DataFrame = pd.read_csv('peer-info/all-peers.csv')
        
    # Filter the df using AND logic
    filtered_peers_df:pd.DataFrame = all_peers_df.copy()
    
    for arg,val in given_args.items(): 
        if val != '' and val != None: 
            filtered_peers_df = filtered_peers_df[filtered_peers_df[arg] == val]
        
    # Return the filtered list of peers
    return jsonify(filtered_peers_df.to_dict(orient='records'))


@fi_bp.route('/ui/get-stored-with-info', methods=['GET'])
@require_localhost
def get_stored_with_info(): 
    '''
        DESC: returns the info for all files that the user is currently storing with other peers (i.e. that other peers are storing for this user).

        ARGS: 
            
            online (int<0|1>) - filter by if the peers are active or not
            allowed_to_receive (int<-1|0|1) - filter by the status of allowed_to_receive from peers 
            public_key (str) - filter by public key
            most_recent_ip (str) - filter by the most recently known IP for peers
            common_name (str) - filter by common name 
            mac_last_four (str) - filter by the last four of the MAC for peers
            
            NOTE: 
                - all args are optional
                - all args are filtered to exact matches 
                - all given args are applied as AND clauses, i.e. only peers that match all given args will be 
                  returned. If an arg is not given or is null/None/empty, that filter is not applied, and args that 
                  do not match the expected type will be ignored
        
        RETURNS: 
        
            - 200 | successful: (dict) a dict with two keys ['matched_peers', 'matched_files'] where 'matched_peers' is a list of dicts containing the
            info for each individual peer that matched at least one file, and 'matched_files' is a list of dicts containing the metadata for each of  
            the individual matched files. 
            - 400 | bad request: if the client supplies an unsupported method or some other error in the client's request.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | server error: if some unexpected error occurs during server-side processing of the request.
        
    '''
    
    # Define expected args for easy checks of given args and their types
    expected_args:dict = {
        'online': int,
        'common_name': str,
        'peer_public_key': str,
        'allowed_to_receive': int,
        'most_recent_ip': str,
        'mac_last_four': str
    }        

    # Filter the request's args to just those that match the formats in expected_args
    given_args:dict = filter_args(expected_args, request)
    
    # Read the current all-peers.csv file as a df
    all_peers_df:pd.DataFrame = pd.read_csv('peer-info/all-peers.csv')

    # Filter the all_peers_df using AND logic
    filtered_peers_df:pd.DataFrame = all_peers_df.copy()
    
    for arg,val in given_args.items(): 
        if val != '' and val != None: 
            filtered_peers_df = filtered_peers_df[filtered_peers_df[arg] == val]
    
    # Read the current "currently-storing-with.csv" file as a df
    curr_storing_with_df:pd.DataFrame = pd.read_csv('peer-info/currently-storing-with.csv')

    # Join the filtered_peers_df with the curr_storing_with_df on "peer_pub_key"
    joined_filtered_df:pd.DataFrame = pd.merge(
        filtered_peers_df[['peer_pub_key', 'common_name']],
        curr_storing_with_df,
        how='right',
        on='peer_pub_key'
    )
    
    # Return the filtered entries
    return jsonify({
        'matched-peers': filtered_peers_df.to_dict(orient='records'),
        'matched-files': joined_filtered_df.to_dict(orient='records')
    })


@fi_bp.route('/ui/whoami', methods=['GET'])
@require_localhost
def whoami(): 
    """
        DESC: returns all info about this user account (i.e. info stored in the config/identity.json file
        plus the user's public key and peer storage path).
        
        RETURNS: 
            - 200 | successful: (dict) a JSON object with all the information about this user account with the following keys: 
            ['pub_key', 'allocated_storage', 'common_name', 'mac'].
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | internal server error: if there is some internal error processing the request.
    """

    # Load the identity config file 
    identity_config:ConfigParser = ConfigParser()
    identity_config.read('config/identity.conf')
                
    # Load this user's public key
    pub_key:str = load_key(
        current_app.enc_config['paths']['PUB_KEY_PATH'],
        'public'
    )
        
    # Create a dict, jsonify and return 
    return jsonify({
        'pub_key': pub_key,
        'allocated_storage': int(identity_config['SETTINGS']['ALLOCATED_STORAGE']),
        'common_name': identity_config['IDENTITY']['COMMON_NAME'],
        'mac': identity_config['IDENTITY']['MAC']
    })


@fi_bp.route('/ui/signup', methods=['POST']) 
@require_localhost
def signup(): 
    """
        DESC: endpoint to create a new account.
        
        REQ BODY: 
            The request body should look like: 
                {
                    "common_name": "<new common name>",
                    "peer_storage_path": "<some filepath>",
                    "allocated_storage": <size in gb>
                }
        RETURNS: 
            - 200 | successful: (dict) a JSON object that contains the info for the newly submitted and accepted request.
            - 400 | bad request: if the user fails to supply the required data.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 409 | conflict: if the user already has an account created.
            - 500 | internal server error: if there is some error in processing the request.
    """

    # --- Request validation --- #
    # Load the current identity config file
    identity_config:ConfigParser = ConfigParser()
    identity_config.read('config/identity.conf')
            
    # Check if there is already a common name for this user (i.e. they already have an account)
    if identity_config['IDENTITY']['COMMON_NAME']: abort(409)
    
    # Extract the body from the request     
    request_body:dict = request.get_json()
        
    # Extract the required keys
    new_common_name:str = request_body.get('common_name', None)
    new_allocated_storage:int = request_body.get('allocated_storage', None)
    new_peer_storage_path:str = request_body.get('peer_storage_path', None)
    
    # Check that the required keys were given, and return bad request if wrong
    try:
        
        # Check that keys are given 
        if not (new_common_name and new_allocated_storage and new_peer_storage_path): raise AttributeError
        
        # Make sure allocated_storage is an integer
        new_allocated_storage = int(new_allocated_storage)
    
    except: 
        # Bad request (missing/invalid info) 
        abort(400) 
    
    # --- Updating identity --- #
    # Update the identity config with the new common name, mac, allocated storage, and peer storage path
    identity_config['IDENTITY']['COMMON_NAME'] = new_common_name
    identity_config['IDENTITY']['MAC'] = get_mac_address() 
    identity_config['SETTINGS']['ALLOCATED_STORAGE'] = new_allocated_storage
    identity_config['PATHS']['PEER_STORAGE_PATH'] = new_peer_storage_path    
    
    # --- Saving new info --- #
    # Create the [new_peer_storage_path] if it does not exist
    os.makedirs(new_peer_storage_path, exist_ok=True)
    
    # Save the updated identity dict
    with open('config/identity.conf', 'w') as file: 
        identity_config.write(file)
    
    # --- Return --- #
    # Return the newly stored info
    return jsonify({
        'common_name': new_common_name,
        'mac': identity_config['IDENTITY']['MAC'],
        'allocated_storage': new_allocated_storage,
        'peer_storage_path': new_peer_storage_path
    })
    
