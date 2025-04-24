
# NOTE: anytime current_app.server is used, CHECK that current_app.server is not null. This enforces that
# the endpoint /ui/init-application/ is (successfully) hit BEFORE anything else happens, because initializing 
# the Server for the app requires the passphrase to load the priv key, thus any use of current_app.server 
# BEFORE /ui/init-application/ is successfully hit will return an error because current_app.server will be 
# None. 

from flask import Blueprint, jsonify, g, current_app, request, abort
import os 
import pandas as pd
from configparser import ConfigParser
from hashlib import sha256
import pandas as pd
import base64
import json
import datetime as dt 

from utils import filter_args, load_key_pem, get_mac_address,get_IP_address, generate_asymm_keys, gen_aes_key, \
    load_aes_key, strip_pem_headers, normalize_string, strip_pem_headers, bytes_to_gb, hash_bytes_sha256

from objects import Server, DatabaseConnection
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
        'most_recent_ip': str,
        'mac_last_four': str
    }        

    # Filter the request's args to just those that match the formats in expected_args
    given_args:dict = filter_args(expected_args, request)

    # Get the matching peers
    matched_peers_df:pd.DataFrame = current_app.db_connection.get_matching_peers(
        peer_pub_key=given_args['peer_pub_key'],
        online=given_args['online'],
        most_recent_ip=given_args['most_recent_ip'],
        common_name=given_args['common_name'],
        mac_last_four=given_args['mac_last_four']
    )
        
    # Return the filtered list of peers
    return jsonify(matched_peers_df.to_dict(orient='records'))


@fi_bp.route('/ui/get-stored-with-info', methods=['GET'])
@require_localhost
def get_stored_with_info(): 
    '''
        DESC: returns the info for all files that the user is currently storing with other peers (i.e. that other peers are storing for this user).

        ARGS: 
            
            online (int<0|1>) - filter by if the peers are active or not
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
        'most_recent_ip': str,
        'mac_last_four': str
    }        

    # Filter the request's args to just those that match the formats in expected_args
    given_args:dict = filter_args(expected_args, request)
    
    # Get the DB connection from the app
    db_connection:DatabaseConnection = current_app.db_connection 
    
    # Get the matched peers from the db
    matched_peers_df:pd.DataFrame = db_connection.get_matching_peers(
        peer_pub_key=given_args['peer_pub_key'],
        online=given_args['online'],
        most_recent_ip=given_args['most_recent_ip'],
        common_name=given_args['common_name'],
        mac_last_four=given_args['mac_last_four']
    )
    
    # Use the matched pub keys to get the storing with info for these peers (or all peers)
    matched_storing_with_df:pd.DataFrame = db_connection.get_storing_with_info(
        list(matched_peers_df['peer_pub_key'].values)
    )
    
    # Return the filtered entries
    return jsonify({
        'matched-peers': matched_peers_df.to_dict(orient='records'),
        'matched-files': matched_storing_with_df.to_dict(orient='records')
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
            - 400 | bad request: if the user is not signed up (i.e. keys don't exist).
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | internal server error: if there is some internal error processing the request.
    """

    # Load the identity config file 
    identity_config:ConfigParser = ConfigParser()
    identity_config.read('config/identity.conf')
    
    try: 
        # Load this user's public key
        pub_key:str = load_key_pem(
            current_app.enc_config['paths']['PUB_KEY_PATH'],
            'public'
        )
            
        # Create a dict, jsonify and return 
        return jsonify({
            'pub_key': strip_pem_headers(pub_key),
            'common_name': identity_config['IDENTITY']['common_name'],
            'mac': identity_config['IDENTITY']['mac'],
            'ip': identity_config['IDENTITY']['ip'],
        })
    
    # Handle exceptions
    except Exception as e:
        return jsonify({
            'error': 'Error loading keys. Is the user signed up?',
            'message': f'{e.__class__}: {e}'
        }), 400

@fi_bp.route('/ui/get-pub-key', methods=['POST'])
@require_localhost
def get_peer_public_key(): 

    try:
        request_body:dict = request.get_json()
        peer_pub_key = pub_key_from_cn(request_body.get('peer_common_name', None))

        return jsonify({
            'peer_pub_key': peer_pub_key
        })
    except Exception as e:
        print(e)

@fi_bp.route('/ui/signup', methods=['POST']) 
@require_localhost
def signup(): 
    """
        DESC: endpoint to create a new account.
            1. Checks if an account already exists.
            2. Updates the identity config file w/ the allocated storage, common name, and peer storage path.
            3. Hashes the passphrase (SHA256) and stores the hash in the enc config file.
            4. Returns the given common name, peer storage path, and allocated storage (not passphrase hash).
        
        REQ BODY: 
            The request body should look like: 
                {
                    "common_name": "<new common name>",
                    "peer_storage_path": "<some filepath>",
                    "allocated_storage": <size in gb>,
                    "passphrase": "<some super secure passphrase>"
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
    if identity_config['IDENTITY']['common_name']: abort(409)
    
    # Extract the body from the request     
    request_body:dict = request.get_json()
        
    # Extract the required keys
    new_common_name:str = request_body.get('common_name', None)
    new_allocated_storage:str = request_body.get('allocated_storage', None)
    new_peer_storage_path:str = request_body.get('peer_storage_path', None)
    new_passphrase:str = request_body.get('passphrase', None) 

    # Check that the required keys were given, and return bad request if wrong
    try:
        # Check that keys are given 
        if not (new_common_name and new_allocated_storage and new_peer_storage_path and new_passphrase): raise AttributeError
        # Make sure allocated_storage is an integer
        new_allocated_storage = float(new_allocated_storage)
    
    except: 
        # Bad request (missing/invalid info) 
        msg = {
            'error': 'Invalid or missing data.',
            'given_params': {
                'common_name': new_common_name,
                'allocated_storage': new_allocated_storage,
                'peer_storage_path': new_peer_storage_path,
                'passphrase': new_passphrase
            }
        }

        print('ERROR: ')
        print(msg)

        return jsonify(msg), 400
    
    # --- Updating identity --- #
    # Update the identity config with the new common name, mac, allocated storage, and peer storage path
    identity_config['IDENTITY']['common_name'] = new_common_name
    identity_config['IDENTITY']['mac'] = get_mac_address()
    identity_config['IDENTITY']['ip'] = get_IP_address()
    identity_config['SETTINGS']['allocated_storage'] = str(new_allocated_storage)
    identity_config['PATHS']['peer_storage_path'] = new_peer_storage_path    
    
    # Encrypt the passphrase in the enc config file
    current_app.enc_config['misc']['pass_hash'] = sha256(new_passphrase.encode()).hexdigest()

    # --- Saving new info --- #
    # Create the [new_peer_storage_path] if it does not exist
    os.makedirs(new_peer_storage_path, exist_ok=True)
    
    # Save the updated identity dict
    with open('config/identity.conf', 'w') as file: 
        identity_config.write(file)
    
    # Resave the enc config with the new passphrase 
    with open('config/encryption.conf', 'w') as file: 
        current_app.enc_config.write(file)

    # Create asymm keys 
    generate_asymm_keys(
        int(current_app.enc_config['keys']['size']),
        int(current_app.enc_config['keys']['exp']),
        current_app.enc_config['paths']['priv_key_path'],
        current_app.enc_config['paths']['pub_key_path'],
        new_passphrase
    )

    # Create a symm key
    gen_aes_key(
        new_passphrase,
        current_app.enc_config['paths']['symm_key_path']
    )

    # --- Return --- #
    # Return the newly stored info
    return jsonify({
        'common_name': new_common_name,
        'mac': identity_config['IDENTITY']['MAC'],
        'allocated_storage': new_allocated_storage,
        'peer_storage_path': new_peer_storage_path
    })
    

@fi_bp.route('/ui/init-application', methods=['POST'])
@require_localhost
def init_application(): 
    """ 
        DESC: endpoint to initialize the application (mainly provide and check the passphrase).

        REQ BODY: 
            The request body should look like: 
                {
                    "passphrase": "<super secure passphrase>"
                }

        RETURNS: 
            - 200 | successful: (dict) a JSON object that contains a "message": "success" if the passphrase is correct
            - 400 | bad request: if the user fails to supply the required data.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost) OR if the passphrase is incorrect OR if the keys don't exist (not signed up).
            - 500 | internal server error: if there is some error in processing the request.
    """

    # Extract the required info from the request 
    request_body:dict = request.get_json()
    given_passphrase:str = request_body.get('passphrase', None)

    # Check that the required info is given
    if not given_passphrase: abort(400)

    print('given_passphrase: ', given_passphrase)
    print('given_passphrase hash: ', sha256(given_passphrase.encode()).hexdigest())
    print('stored hash: ', current_app.enc_config['misc']['pass_hash'])
    
    # Check the given passphrase with the stored hash
    if current_app.enc_config['misc']['pass_hash'] != sha256(given_passphrase.encode()).hexdigest(): 
        abort(403)

    # Load the keys 
    try: 
        pub_key_pem:str = load_key_pem(current_app.enc_config['paths']['pub_key_path'], 'public')
        priv_key_pem:str = load_key_pem(current_app.enc_config['paths']['priv_key_path'], 'private', given_passphrase)
        symm_key_b64:str = load_aes_key(given_passphrase, current_app.enc_config['paths']['symm_key_path'])
        
    # Handle exceptions
    except Exception as e:
        
        # Log 
        current_app.logger.warning(f'Caught exception loading keys in init_application() - {e.__class__}: {e}') 
        
        # Exception (likely) means that the user hasn't signed up yet
        return jsonify({
            'error': 'There was an error loading the keys. Has the user signed up yet?',
        }), 403
    
    # Construct paths for the server
    server_log_filepath:str = os.path.join(current_app.flask_config['paths']['LOGS_DIR'], 'server.log')
    server_db_log_filepath:str = os.path.join(current_app.flask_config['paths']['LOGS_DIR'], 'server-database.log')
    
    # Init a Server obj 
    server:Server = Server(
        pub_key_pem,                                                # pub_key_pem
        priv_key_pem,                                               # priv_key_pem
        symm_key_b64,                                               # symm_aes_key
        current_app.identity_config['IDENTITY']['common_name'],     # common_name
        current_app.network_config['network']['IFACE'],             # iface
        current_app.network_config['network']['PORT'],              # port
        current_app.network_config['network']['IFACE'],             # mcast_iface
        current_app.network_config['multicast']['MCAST_PORT'],      # mcast_port
        current_app.network_config['multicast']['MCAST_GROUP'],     # mcast_group
        DatabaseConnection(                                         # send_db_connection
            current_app.flask_config['paths']['DB_PATH'],
            log_filepath=server_db_log_filepath,
            logger_name='server_db_logger'
        ),                                 
        current_app.flask_config['paths']['DB_PATH'],           # db_filepath
        current_app.identity_config['PATHS']['peer_storage_path'], # peer_storage_dir
        log_filepath=server_log_filepath,                          # log_filepath
        db_log_filepath=server_db_log_filepath,                    # db_log_filepath
        db_logger_name='server_db_logger'                          # db_logger_name
    )
    
    # TODO: call server.send_mcast_hello()
    # DO SOMETHING ...
    
    # Add the server to the current app 
    current_app.server = server
    
    # Return success 
    return jsonify({
        'status': 'success'
    })
    

@fi_bp.route("/ui/get-all-info", methods=['GET'])
@require_localhost
def get_all_info(): 
    """
        DESC: returns all info about this storage of this user. Extracts information from the
        peer-info folder (i.e. all-peers.csv, currently-storing-for.csv, currently-storing-with.csv, and previously-shared-with.csv)
        
        RETURNS: 
            - 200 | successful: (dict) a JSON object with all the information about this user sharing history with the following keys: 
            {userID: ...,
              stored-for:  [{filename: ..., filesize:..., filehash:...},...], 
              stored-with: [{filename: ..., filesize:..., filehash:...},...],
              shared-with: [{filename: ..., filesize:..., filehash:...},...]
            }
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | internal server error: if there is some internal error processing the request.
    """

    # Get the app db connection
    db_connection:DatabaseConnection = current_app.db_connection
    
    # Read each of the CSVs into dataframes
    all_peers_df:pd.DataFrame = db_connection.table_as_df('Peer')
    storing_for_df:pd.DataFrame = db_connection.table_as_df('CurrentlyStoringFor')
    storing_with_df:pd.DataFrame = db_connection.table_as_df('CurrentlyStoringWith')
    shared_with_df:pd.DataFrame = db_connection.table_as_df('PreviouslySharedWith')

    # TODO: group the file lists BY user? and send a list of user 
    # DO SOMETHING ... 
    # ...
    
    # Return the filtered entries
    return jsonify({
        'peer_list': all_peers_df.to_dict(orient='records'),
        'storing_with': storing_with_df.to_dict(orient='records'),
        'storing_for': storing_for_df.to_dict(orient='records'),
        'shared_with': shared_with_df.to_dict(orient='records')
    })


@fi_bp.route("/ui/get-interacted-with-peers", methods=['GET'])
@require_localhost
def get_interacted_with_peers():
    """ 
    
    """

    # Use the app's DB connection to get the map of interacted with peers
    return jsonify({
        'user_data': current_app.db_connection.get_interacted_with_peers()
    })


@fi_bp.route('/ui/get-storage-info', methods=['GET'])
@require_localhost
def get_storage_info(): 
    """
        DESC: returns AMOUNT of storage currently storing for, with, and previously shared.
        
        RETURNS: 
            - 200 | successful: (dict) a JSON object with all the storage amounts. 
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | internal server error: if there is some internal error processing the request.
    """

    # Use the app's DB connection to get the storage info for all relevant tables
    return jsonify(current_app.db_connection.get_all_storage_info())


@fi_bp.route('/ui/get-user-history', methods=['GET'])
@require_localhost
def get_user_history(): 
    """
        DESC: Returns the history of this client with the given peer (ID'd via public key).
        
        ARGUMENTS: 
            peer_pub_key (str, optional): optionally specify a specific peer to get this client's history with. Defaults to None (all peers).
            
        RETURNS: 
            - 200 | successful: (dict) a JSON object with three keys for "storing_with", "storing_for", "shared", where each value is a list of dicts containing the matched info.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | internal server error: if there is some internal error processing the request.
    """
    
    # Get the arguments from the request
    peer_pub_key:str = request.args.get('peer_pub_key', None)
    
    # Use the app's db connection to retrieve the requested data
    return jsonify(current_app.db_connection.get_user_history(peer_pub_key=peer_pub_key))

@fi_bp.route('/ui/get-user-history-specific', methods=['POST'])
@require_localhost
def get_user_history_specific(): 
    try:
        request_body:dict = request.get_json()
        other_user:str = pub_key_from_cn(request_body.get('other_user', None))
        print(other_user)

        storing_for_df = pd.read_csv('peer-info/currently-storing-for.csv')
        storing_with_df = pd.read_csv('peer-info/currently-storing-with.csv')
        shared_with_df = pd.read_csv('peer-info/previously-shared-with.csv')

    # Check if given a peer to filter by 
    if peer_pub_key: 

        # Filter each of the dfs to the given peer pub key
        filtered_storing_for_df:pd.DataFrame = storing_for_df.loc[storing_for_df['peer_pub_key'] == peer_pub_key]
        filtered_storing_with_df:pd.DataFrame = storing_with_df.loc[storing_with_df['peer_pub_key'] == peer_pub_key]
        filtered_shared_df:pd.DataFrame = shared_with_df.loc[shared_with_df['peer_pub_key'] == peer_pub_key]

    # If not given a pub key to filter, then use all the data 
    else: 
        filtered_storing_for_df:pd.DataFrame = storing_for_df
        filtered_storing_with_df:pd.DataFrame = storing_with_df
        filtered_shared_df:pd.DataFrame = shared_with_df

    # Return the requested data
    return jsonify({
        'storing_for': filtered_storing_for_df.to_dict(orient='records'),
        'storing_with': filtered_storing_with_df.to_dict(orient='records'),
        'shared': filtered_shared_df.to_dict(orient='records')
    })

@fi_bp.route('/ui/get-user-history-specific', methods=['POST'])
@require_localhost
def get_user_history_specific(): 
    try:
        request_body:dict = request.get_json()
        other_user:str = pub_key_from_cn(request_body.get('other_user', None))
        print(other_user)

        storing_for_df = pd.read_csv('peer-info/currently-storing-for.csv')
        storing_with_df = pd.read_csv('peer-info/currently-storing-with.csv')
        shared_with_df = pd.read_csv('peer-info/previously-shared-with.csv')

        data = pd.concat([storing_for_df, storing_with_df, shared_with_df], ignore_index=True)
        filtered_data = data[data['peer_pub_key'] == other_user]

        filtered_json_data = json.loads(filtered_data.to_json(orient='records'))
        return jsonify({
            'user_data': filtered_json_data
        })
    except Exception as e:
        print(e)

@fi_bp.route('/ui/peer-cn-to-pub-key', methods=['GET'])
@require_localhost
def peer_cn_to_pub_key(): 
    """
        DESC: returns the public key for the given peer common name.
        
        ARGUMENTS: 
            peer_common_name (str): the common name of the peer. 
            
        RETURNS: 
            - 200 | successful: (dict) a JSON object with a single key "peer_pub_key".
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 404 | not found: if the given common name does not exist in the DB.
            - 500 | internal server error: if there is some internal error processing the request.
            
    """
    
    # Get the peer_common_name from the request 
    peer_cn:str = request.args.get('peer_common_name', None) 
    
    # Check that a CN was given 
    if not peer_cn: 
        return jsonify({
            'error': 'Not given a peer_common_name.'
        }), 400
        
    # Convert the CN to pub key
    matched_pub_keys:str = current_app.db_connection.pub_key_from_cn(peer_cn)

    # Check if results
    if not matched_pub_keys: 
        return jsonify({
            'error': f'Common name "{peer_cn}" does not match any known peers.'
        }), 404
        
    # Return the requested information
    return jsonify({
        'peer_pub_key': matched_pub_keys[0] if len(matched_pub_keys) == 1 else matched_pub_keys
    })


@fi_bp.route('/ui/get-pending-requests', methods=['GET'])
@require_localhost
def get_pending_requests(): 
    """ 
        DESC: returns a list of all pending requests (incoming and outgoing). NOTE: to get the number of incoming or outgoing reqs, take the length of
        the list of dicts for that key. For example, in JS: 
        
            ```js 
                // Make API req
                const response = await fetch(...);
                const responseJson = await response.json();
                
                // Extract lists of incoming and outgoing requests 
                const incomingRequests = responseJson.incoming_requests;
                const outgoingRequests = responseJson.outgoing_requests;
                
                // Get the number of incoming and outgoing requests 
                const numIncomingRequests = incomingRequests.length;
                const numOutgoingRequests = outgoingRequests.length; 
            ```
            
        ARGUMENTS:
            *Endpoint takes no arguments*
            
        RETURNS: 
            - 200 | successful: (dict) a JSON object with two keys for "incoming_requests" and "outgoing_requests" and the values are lists of dicts with the data for each (sorted by date desc).
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | internal server error: if there is some internal error processing the request.
    """
    
    # Use the app's DB connection to get the pending requests as a df 
    pending_requests_df:pd.DataFrame = current_app.db_connection.table_as_df('PendingRequests') 
    
    # Filter into incoming and outgoing requests and return
    return jsonify({
        'incoming_requests': pending_requests_df.loc[pending_requests_df['direction'] == 'incoming'].to_dict(orient='records'),
        'outgoing_requests': pending_requests_df.loc[pending_requests_df['direction'] == 'outgoing'].to_dict(orient='records')
    })


@fi_bp.route('/ui/upload-data', methods=['POST'])
@require_localhost
def upload_data(): 
    
    # Get the app's db connection
    db_connection:DatabaseConnection = current_app.db_connection
    
    # Extract the args from the form
    peer_pub_key:str = request.form.get('peer_pub_key', "")
    send_method:str = request.form.get('send_method', "")
    uploaded_files:list = request.files.getlist('files')
        
    # Check that required info is given
    if not peer_pub_key or not send_method or len(uploaded_files) == 0: 
        return jsonify({
            'error': 'Failed to supply the required arguments.',
            'given_args': {
                'peer_pub_key': peer_pub_key,
                'send_method': send_method,
                'num_uploaded_files': len(uploaded_files)
            }
        })
    
    try:
        # Iterate over the files
        for file in uploaded_files:
            
            # Get the file contents, then the size and hash
            file_bytes:bytes = file.read()
            file_size_gb:float = bytes_to_gb(len(file_bytes))
            file_hash:str = hash_bytes_sha256(file_bytes)
                        
            # Add a row in the PendingRequests table for this file
            db_connection.new_pending_request(
                'outgoing',         # direction
                send_method,        # request_type
                peer_pub_key,       # peer_pub_key
                file.filename,      # filename
                file_size_gb,       # size_gb
                file_hash           # sha256
            )
        
        # Return status
        return jsonify({'status': 'success'})    
    
    except Exception as e:
        return jsonify({
            'error': e
        }), 500
        
        
@fi_bp.route('/ui/reupload-data', methods=['POST'])
@require_localhost
def reupload_data():
    
    # NOTE: only need the [peer_pub_key] and [filename] to match an outgoing request
    # Extract the given data
    peer_pub_key = request.form.get("peer_pub_key", "")
    filename = request.form.get("file", "")
    
    # Check that required info is given 
    if not all([peer_pub_key, filename]):
        return jsonify({
            'error': 'Failed to supply the required data.',
            'given_args': {
                'peer_pub_key': peer_pub_key,
                'file': filename
            }
        }), 400
    
    # Get the app's db connection
    db_connection:DatabaseConnection = current_app.db_connection
    
    try:
    
        # Get the ID of the pending request that matches the given information (outgoing reqs only)
        req_id:int = db_connection.get_request_id(
            peer_pub_key,     # peer_pub_key
            filename,         # filename
            'outgoing'        # direction (static, outgoing)
        )

        # Check that we got a match
        if req_id == -1: 
            return jsonify({
                'error': 'No requests match the given information',
                'given_args': {
                    'peer_pub_key': peer_pub_key,
                    'file': filename
                }
            }), 404
            
        # Update the date of the request to the new date
        db_connection.update_request_date(
            req_id,
            dt.datetime.now().strftime('%Y-%m-%d')
        )
        
        # Return status
        return jsonify({'status': 'success'})
    
    except Exception as e:
        print(f"Error in reupload_data: {e}")
        return jsonify({"error": str(e)})

