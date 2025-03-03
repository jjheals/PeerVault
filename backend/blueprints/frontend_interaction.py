
from flask import Blueprint, jsonify, g, current_app, request, abort
import json 
import pandas as pd

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
        DESC: endpoint to get the current state of the peer list JSON file.
        
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
        'public_key': str,
        'allowed_to_receive': int,
        'most_recent_ip': str,
        'mac_last_four': str
    }        

    # Filter the request's args to just those that match the formats in expected_args
    given_args:dict = filter_args(expected_args, request)

    # Read the current all-peers.json file
    with open('peer_storage/all-peers.json', 'r') as file: 
        all_peers:dict[str, dict[str, any]] = json.load(file)

        # Convert to df for easier filtering and returning 
        all_peers_df:pd.DataFrame = pd.DataFrame.from_dict(all_peers, orient='index').reset_index().rename(columns={'index': 'public_key'})
        
    # Filter the df using AND logic
    filtered_peers_df:pd.DataFrame = all_peers_df.copy()
    
    for arg,val in given_args.items(): 
        if val != '' and val != None: 
            filtered_peers_df = filtered_peers_df[filtered_peers_df[arg] == val]
        
    # Return the filtered list of peers
    return jsonify(filtered_peers_df.to_dict(orient='records'))


@fi_bp.route('/ui/get-stored-files', methods=['GET'])
@require_localhost
def get_all_stored_files(): 
    '''
        DESC: returns the info for all files that the user is currently storing on other peers that 
        match the provided filters. 
        
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
        
        
    '''
    
    # Define expected args for easy checks of given args and their types
    expected_args:dict = {
        'online': int,
        'common_name': str,
        'public_key': str,
        'allowed_to_receive': int,
        'most_recent_ip': str,
        'mac_last_four': str
    }        

    # Filter the request's args to just those that match the formats in expected_args
    given_args:dict = filter_args(expected_args, request)
    
    # Read the current all-peers.json file
    with open('peer-data/all-peers.json', 'r') as file: 
        all_peers:dict[str, dict[str, any]] = json.load(file)

        # Convert to df for easier filtering and returning 
        all_peers_df:pd.DataFrame = pd.DataFrame.from_dict(all_peers, orient='index').reset_index().rename(columns={'index': 'public_key'})
        
    # Filter the df using AND logic
    filtered_peers_df:pd.DataFrame = all_peers_df.copy()
    
    for arg,val in given_args.items(): 
        if val != '' and val != None: 
            filtered_peers_df = filtered_peers_df[filtered_peers_df[arg] == val]

    print(filtered_peers_df.head())
    
    # Extract the "files_stored_with" col from the filtered df and reorient to include the pub key and common name
    filtered_entries:dict = {}
    
    for _, row in filtered_peers_df.iterrows(): 
        
        # Create a new entry for this row
        filtered_entries[row['public_key']] = {
            'common_name': row['common_name'],
            'mac_last_four': row['mac_last_four'],
            'files_stored_with': row['files_stored_with']
        }
        
    # Return the filtered entries
    return jsonify(filtered_entries)


@fi_bp.route('/ui/whoami', methods=['GET'])
@require_localhost
def whoami(): 
    """
        DESC: returns all info about this user account (i.e. info stored in the config/identity.json file
        plus the user's public key).
        
        RETURNS: 
            - 200 | successful: (dict) a JSON object with all the information about this user account.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | internal server error: if there is some internal error processing the request.
    """
    
    # Load the identity JSON 
    with open('config/identity.json', 'r') as file: 
        identity_dict:dict = json.load(file)
                
    # Load this user's public key
    pub_key:str = load_key(
        current_app.enc_config['paths']['PUB_KEY_PATH'],
        'public'
    )
        
    # Add the public key to the identity dict
    identity_dict['pub-key'] = pub_key
    
    # Jsonify and return
    return jsonify(identity_dict)


@fi_bp.route('/ui/signup', methods=['POST']) 
@require_localhost
def signup(): 
    """
        DESC: endpoint to create a new account.
        
        REQ BODY: 
            The request body should look like: 
                {
                    "common-name": "<new common name>"
                }
        RETURNS: 
            - 200 | successful: (dict) a JSON object that contains the info for the newly submitted request.
            - 400 | bad request: if the user fails to supply the required data.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 409 | conflict: if the user already has an account created.
            - 500 | internal server error: if there is some error in processing the request.
    """

    # Load the current identity json file
    with open('config/identity.json', 'r') as file: 
        identity_dict:dict = json.load(file)
        
    print('curr identity dict: ', identity_dict)
    
    # Check if there is already a common name for this user (i.e. they already have an account)
    if identity_dict['common-name']: 
        
        # User already has an account
        abort(409)
    
    # Extract the body from the request     
    request_body:dict = request.get_json()
        
    # Extract the required keys
    new_common_name:str = request_body.get('common-name', None)
    
    # Check that the required keys were given
    if not new_common_name: 
        
        # Bad request (missing info) 
        abort(400) 
        
    # Update the identity dict with the new common name
    identity_dict['common-name'] = new_common_name
    
    # Get the device's MAC anad store in the identity dict
    print('getting mac')
    identity_dict['mac'] = get_mac_address() 
    
    print('new identity dict: ', identity_dict)
    
    # Save the updated identity dict
    with open('config/identity.json', 'w+') as file: 
        json.dump(identity_dict, file, indent=4)
        
    # Return the newly stored info
    return jsonify(identity_dict)
    
    