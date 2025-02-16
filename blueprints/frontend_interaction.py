
from flask import Blueprint, jsonify, g, request, abort
import json 
import pandas as pd


# ---- Config & init ---- #
# Create blueprint
fi_bp:Blueprint = Blueprint('frontend_interaction', __name__)


# ---- Add endpoints ---- #
@fi_bp.route('/api/get-peer-list', methods=['GET'])
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
            - 500 | server error: if some unexpected error occurs during server-side processing of the request.
    '''
    
    # Define expected args for easy checks of given args and their types
    expected_args:dict = {
        'online': int,
        'common_name': str,
        'public_key': str
    }        

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
        
    # Return the filtered list of peers
    return jsonify(filtered_peers_df.to_dict(orient='records'))