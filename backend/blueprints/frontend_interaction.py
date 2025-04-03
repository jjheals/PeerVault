
import json
from flask import Blueprint, jsonify, g, current_app, request, abort
import os 
import pandas as pd
import numpy as np 
from configparser import ConfigParser
from hashlib import sha256
import csv
import pandas as pd

from utils import filter_args, load_key_pem, get_mac_address, hash_bytes_sha256, getCommonNameFromPubKey, getPubKeyFromCommonName, getUniquePeers
from .funcs import require_localhost
from werkzeug.utils import secure_filename

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
    pub_key:str = load_key_pem(
        current_app.enc_config['paths']['PUB_KEY_PATH'],
        'public'
    )
    print(identity_config['IDENTITY']['COMMON_NAME'])
        
    # Create a dict, jsonify and return 
    return jsonify({
        'pub_key': pub_key,
        'common_name': identity_config['IDENTITY']['COMMON_NAME'],
        'mac': identity_config['IDENTITY']['MAC'],
        'ip': identity_config['IDENTITY']['IP'],
    })


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
    if identity_config['IDENTITY']['COMMON_NAME']: abort(409)
    
    # Extract the body from the request     
    request_body:dict = request.get_json()
        
    # Extract the required keys
    new_common_name:str = request_body.get('common_name', None)
    new_allocated_storage:int = request_body.get('allocated_storage', None)
    new_peer_storage_path:str = request_body.get('peer_storage_path', None)
    new_passphrase:str = request_body.get('passphrase', None) 

    # Check that the required keys were given, and return bad request if wrong
    try:
        
        # Check that keys are given 
        if not (new_common_name and new_allocated_storage and new_peer_storage_path and new_passphrase): raise AttributeError
        
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
    
    # Encrypt the passphrase in the enc config file
    current_app.enc_config['misc']['PASS_HASH'] = sha256(str(new_passphrase)).hexdigest()

    # --- Saving new info --- #
    # Create the [new_peer_storage_path] if it does not exist
    os.makedirs(new_peer_storage_path, exist_ok=True)
    
    # Save the updated identity dict
    with open('config/identity.conf', 'w') as file: 
        identity_config.write(file)
    
    # Resave the enc config with the new passphrase 
    with open('config/encryption-config.conf', 'w') as file: 
        current_app.enc_config.write(file)

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
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost) OR if the passphrase is incorrect.
            - 500 | internal server error: if there is some error in processing the request.
    """

    # Extract the required info from the request 
    request_body:dict = request.get_json()
    given_passphrase:str = request_body.get('passphrase', None)

    # Check that the required info is given
    if not given_passphrase: abort(400)

    # Check the given passphrase with the stored hash
    if current_app.enc_config['misc']['PASS_HASH'] != sha256(given_passphrase): 
        abort(403)

    # Return success 
    return jsonify({
        'status': 'success'
    })
    

@fi_bp.route("/ui/get-all-info", methods=['GET'])
@require_localhost
def get_all_sharing_info_application(): 
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

    # open all-peers.csv
    all_peers = []

    with open('peer-info/all-peers.csv', 'r', newline='') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header row
            
            for row in reader:
                if len(row) < 3:
                    continue  # Skip rows with missing data

                try:
                    all_peers.push(row)
                except ValueError:
                    print(f"Skipping invalid row: {row}")  # Debugging info

        


    # # open currently-storing-for.csv
    storing_for = []

    with open('peer-info/currently-storing-for.csv', 'r', newline='') as f2:
            reader = csv.reader(f2)
            next(reader, None)  # Skip header row
            
            for row in reader:
                if len(row) < 3:
                    continue  # Skip rows with missing data

                try:
                    storing_for.push(row)
                except ValueError:
                    print(f"Skipping invalid row: {row}")  # Debugging info

        

    # # open currently-storing-with.csv
    storing_with = []

    with open('peer-info/currently-storing-with.csv', 'r', newline='') as f3:
            reader = csv.reader(f3)
            next(reader, None)  # Skip header row
            
            for row in reader:
                if len(row) < 3:
                    continue  # Skip rows with missing data

                try:
                    storing_with.push(row)
                except ValueError:
                    print(f"Skipping invalid row: {row}")  # Debugging info

        

    # # open currently-sharing-with.csv
    sharing_with = []

    with open('peer-info/previously-shared-with.csv', 'r', newline='') as f4:
            reader = csv.reader(f4)
            next(reader, None)  # Skip header row
            
            for row in reader:
                if len(row) < 3:
                    continue  # Skip rows with missing data

                try:
                    sharing_with.push(row[0])
                except ValueError:
                    print(f"Skipping invalid row: {row}")  # Debugging info


# We have a list of peers that we have interacted with
    # group the file lists BY user? and send a list of user 
        
    # Return the filtered entries
    return jsonify({
        'peer-list': all_peers,
        'shared-with': sharing_with,
        'stored-with': storing_with,
        'stored-for': storing_for
    })


@fi_bp.route("/ui/get-sharing-peers", methods=['GET'])
@require_localhost
def get_sharing_name(): 
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
    unique_peers = getUniquePeers()

    return jsonify({
        'peer-list': unique_peers
    })


@fi_bp.route("/ui/get-shared-by-peer", methods=['GET'])
@require_localhost
def get_total_shared_by_user():

    unique_peers = getUniquePeers()

    peer_data = []

    for user in unique_peers:
        stored_locally = 0
        stored_remotely = 0
        shared = 0

        with open('peer-info/currently-storing-for.csv', 'r', newline='') as f2:
            reader = csv.reader(f2)
            next(reader, None)  # Skip header row
            
            for row in reader:
                if len(row) < 3:
                    continue  # Skip rows with missing data

                if row[0] == user:      
                    try:
                        stored_locally += float(row[2])
                    except Exception as e:
                        print("Error: ", {e})


        with open('peer-info/currently-storing-with.csv', 'r', newline='') as f3:
            reader = csv.reader(f3)
            next(reader, None)  # Skip header row
            
            for row in reader:
                if len(row) < 3:
                    continue  # Skip rows with missing data

                if row[0] == user: 
                    try:
                        stored_remotely += float(row[2])
                    except Exception as e:
                        print("Error: ", {e})


        with open('peer-info/previously-shared-with.csv', 'r', newline='') as f4:
            reader = csv.reader(f4)
            next(reader, None)  # Skip header row
            
            for row in reader:
                if len(row) < 3:
                    continue  # Skip rows with missing data

                if row[0] == user: 
                    try:
                        shared += float(row[3])
                    except Exception as e:
                        print("Error: ", {e})
       
        peer_data.append(
            {"user": user,
             "common_name": getCommonNameFromPubKey(user),
                    "storage_data" : 
                    {
                        'stored_remotely': stored_remotely,
                        'stored_locally': stored_locally,
                        'shared': shared
                    }
            }
        )

    return jsonify({
        'user_data': peer_data
    })



@fi_bp.route('/ui/get-shared-storage', methods=['GET'])
@require_localhost
def get_shared_storage(): 
    """
        DESC: returns AMOUNT of shared storage
        
        RETURNS: 
            - 200 | successful: (dict) a JSON object with all the information about this user account with the following keys: 
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | internal server error: if there is some internal error processing the request.
    """

    numBytes = 0

    with open('peer-info/previously-shared-with.csv', 'r', newline='') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header row
            
            for row in reader:
                if len(row) < 3:
                    continue  # Skip rows with missing data

                try:
                    numBytes += float(row[3])
                except ValueError:
                    print(f"Skipping invalid row: {row}")  # Debugging info

        
    # Create a dict, jsonify and return 
    return jsonify({
        'storage': numBytes,
    })



@fi_bp.route('/ui/get-local-storage', methods=['GET'])
@require_localhost
def get_local_storage(): 
    """
        DESC: returns amount of local storage
        
        RETURNS: 
            - 200 | successful: (dict) a JSON object with all the information about this user account with the following keys: 
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | internal server error: if there is some internal error processing the request.
    """

    numBytes = 0

    with open('peer-info/currently-storing-for.csv', 'r', newline='') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header row
            
            for row in reader:
                if len(row) < 3:
                    continue  # Skip rows with missing data

                try:
                    numBytes += float(row[2])
                except ValueError:
                    print(f"Skipping invalid row: {row}")  # Debugging info

        
    # Create a dict, jsonify and return 
    return jsonify({
        'storage': numBytes,
    })



@fi_bp.route('/ui/get-remote-storage', methods=['GET'])
@require_localhost
def get_remote_storage(): 
    """
        DESC: returns amount of remote storage
        
        RETURNS: 
            - 200 | successful: (dict) a JSON object with all the information about this user account with the following keys: 
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 500 | internal server error: if there is some internal error processing the request.
    """

    numBytes = 0

    with open('peer-info/currently-storing-with.csv', 'r', newline='') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header row
            
            for row in reader:
                if len(row) < 3:
                    continue  # Skip rows with missing data

                try:
                    numBytes += float(row[2])
                except ValueError:
                    print(f"Skipping invalid row: {row}")  # Debugging info
        
    # Create a dict, jsonify and return 
    return jsonify({
        'storage': numBytes,
    })    


@fi_bp.route('/ui/get-user-history', methods=['POST'])
@require_localhost
def get_user_history(): 

    try:
        request_body:dict = request.get_json()
        other_user:str = getPubKeyFromCommonName(request_body.get('other_user', None))
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


@fi_bp.route('/ui/get-pub-key', methods=['POST'])
@require_localhost
def get_peer_public_key(): 

    try:
        request_body:dict = request.get_json()
        peer_pub_key = getPubKeyFromCommonName(request_body.get('peer_common_name', None))
        print(peer_pub_key)

        return jsonify({
            'peer_pub_key': peer_pub_key
        })
    except Exception as e:
        print(e)


@fi_bp.route('/ui/get-sent-requests', methods=['GET'])
@require_localhost
def get_sent_requests(): 

    try:
        all_requests:pd.DataFrame = pd.read_csv('requests/sent_requests.csv')
        output = all_requests.to_dict(orient='records')
        return jsonify({
            'all_requests': output
        })
    except Exception as e:
        print(e)


@fi_bp.route('/ui/get-incoming-requests', methods=['GET'])
@require_localhost
def get_incoming_requests(): 

    try:
        all_requests:pd.DataFrame = pd.read_csv('requests/incoming_requests.csv')
        output = all_requests.to_dict(orient='records')
        return jsonify({
            'all_requests': output
        })
    except Exception as e:
        print(e)


@fi_bp.route('/ui/get-universal-requests', methods=['GET'])
@require_localhost
def get_universal_requests(): 

    try:
        all_requests:pd.DataFrame = pd.read_csv('requests/universal_outgoing_requests.csv')
        output = all_requests.to_dict(orient='records')
        return jsonify({
            'all_requests': output
        })
    except Exception as e:
        print(e)


@fi_bp.route('/ui/get-num-requests', methods=['GET'])
@require_localhost
def get_num_requests(): 

    try:
        incoming:pd.DataFrame = pd.read_csv('requests/incoming_requests.csv')
        num_incoming = (incoming.size) / 5

        direct:pd.DataFrame = pd.read_csv('requests/sent_requests.csv')
        num_direct = (direct.size) / 5

        uni:pd.DataFrame = pd.read_csv('requests/universal_outgoing_requests.csv')
        num_uni = (uni.size) / 4

        return jsonify({
            'incoming': num_incoming,
            'direct': num_direct,
            'universal': num_uni
        })
    except Exception as e:
        print(e)
        
        
@fi_bp.route('/ui/send-file', methods=['POST']) 
def send_file(): 
    """Endpoint to initiate the process of sending (sharing or storing) a file with another peer.
    
    REQ BODY: 
        The request body should be form data (JS obj FormData). There should also be a file attached to the 
        request - in JS do this with: 
            
            ```javascript
                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('code', '<CODE>');
                formData.append('peer_pub_key': '<PUBLIC KEY>')
                
                // Use formData as the request body ... 
                // ... 
            ```
        
        NOTE: 
            - If code is blank or any code other than "SHARE" or "STORE" is provided, the request will be
              dropped and the server will return HTTP 400 (Bad Request).
            - If the peer_pub_key is empty string, then the server will initiate a broadcast message to find 
              a recipient that is online.
    
    RETURNS: 
        - 200 | successful: (dict) a JSON object that contains the info of the peer that the file was sent to (or is pending to be sent to) 
        - 400 | bad request: if the user fails to supply the required data OR if the provided data is invalid.
        - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
        - 406 | not acceptable: if a peer with the given public key is not found. 
        - 500 | internal server error: if there is some error in processing the request.
    """
    
    # Extract req body
    request_json:dict = request.form.to_dict()
    
    # Extract data from req body
    try: 
        given_code:str = request_json['code']
        peer_pub_key:str = request_json['peer_pub_key']
        file:bytes = request.files['file']
    
        # Validate given code
        if not given_code or not given_code.upper() in ['SHARE', 'STORE']:
            print(f'\033[91mERROR in fi_bp.send_file(): \033[0minvalid code given. Got "{given_code}"')
            abort(400) 
        
    # Exception means a key error or something else was wrong about the request 
    except Exception as e: 
        print('\033[91mERROR in fi_bp.send_file(): \033[0m', e)
        abort(400)

    # Extract the filename and file contents
    filename:str = secure_filename(file.filename)
    file_content:bytes = file.read()
    
    # Return the pointer to the beginning of the file
    file.seek(0)
    
    # Init vars for the peer's IP and online status
    peer_ip:str = None
    peer_online_status:bool = None
    
    # Check if we're finding a recipient or if we were given a public key to send to
    if peer_pub_key: 
        
        # Load the all peers df so we can convert the public key to an IP address
        all_peers_df:pd.DataFrame = pd.read_csv('peer-info/all-peers.csv')
        
        # Get the row that matches this public key
        row:np.ndarray = all_peers_df.loc[all_peers_df['peer_pub_key'] == peer_pub_key]
        
        # Get the most recent IP and online status if a match was found
        if row and not row.empty:
            peer_ip:str = row.iloc[0]['most_recent_ip']
            peer_online_status:bool = row.iloc[0]['online']    
        else: 
            # No match was found, return HTTP 406 (Not Acceptable) 
            abort(406)
    
    # Find a recipient using multicast
    else: 
        # TODO: implement multicast message to find a recipient
        # DO SOMETHING ... 
        return jsonify({'status': 200, 'message': 'Implementation for finding a recipient is not complete.'})

    # Act according to the code
    # SHARE request
    if given_code.upper() == 'SHARE': 
        
        # TODO: Use current_app.server to call Server.send_share_request()
        # DO SOMETHING ...
        
        #try: 
        #   current_app.server.send_share_request(
        #       peer_ip,
        #       file_content,
        #       filename
        #   )
        #except Exception as e: 
        #   HANDLE EXCEPTION 
        # 
        
        pass
        
    # STORE request
    else: 
        # TODO: Use current_app.server to call Server.send_share_request()
        # DO SOMETHING ...
        
        #try: 
        #   current_app.server.send_store_request(
        #       peer_ip,
        #       file_content,
        #       filename
        #   )
        #except Exception as e: 
        #   HANDLE EXCEPTION 
        # 
   
        pass 
    
    # Send back a message confirming the request was received
    return jsonify({
        'message': 'Share request sent' if peer_online_status else 'Peer is offline - send queued.',
        'peer_pub_key': peer_pub_key,
        'peer_ip': peer_ip,
        'common_name': row.iloc[0]['common_name']
    })