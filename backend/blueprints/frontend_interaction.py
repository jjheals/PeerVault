
# NOTE: anytime current_app.server is used, CHECK that current_app.server is not null. This enforces that
# the endpoint /ui/init-application/ is (successfully) hit BEFORE anything else happens, because initializing 
# the Server for the app requires the passphrase to load the priv key, thus any use of current_app.server 
# BEFORE /ui/init-application/ is successfully hit will return an error because current_app.server will be 
# None. 

import json
from flask import Blueprint, jsonify, g, current_app, request, abort
import os 
import pandas as pd
from configparser import ConfigParser
from hashlib import sha256
import csv
import pandas as pd
import datetime

from utils import filter_args, load_key_pem, get_mac_address, getCommonNameFromPubKey, getPubKeyFromCommonName, getUniquePeers
from objects import Server 

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

    # Load the keys 
    pub_key_pem:str = load_key_pem(current_app.enc_config['paths']['PUB_KEY_PATH'])
    priv_key_pem:str = load_key_pem(current_app.enc_config['paths']['PRIV_KEY_PEM'], given_passphrase)
    
    # Init a Server obj 
    server:Server = Server(
        pub_key_pem,                                                # pub_key_pem
        priv_key_pem,                                               # priv_key_pem
        current_app.identity_config['IDENTITY']['common_name'],     # common_name
        current_app.network_config['network']['IFACE'],             # iface
        current_app.network_config['network']['PORT'],              # port
        current_app.network_config['network']['IFACE'],             # mcast_iface
        current_app.network_config['multicast']['MCAST_PORT'],      # mcast_port
        current_app.network_config['multicast']['MCAST_GROUP'],     # mcast_group
        'peer-info/'                                                # data_dir_path
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

    # Read each of the CSVs into dataframes
    all_peers_df:pd.DataFrame = pd.read_csv('peer-info/all-peers.csv')
    storing_for_df:pd.DataFrame = pd.read_csv('peer-info/currently-storing-for.csv')
    storing_with_df:pd.DataFrame = pd.read_csv('peer-info/currently-storing-with.csv')
    shared_with_df:pd.DataFrame = pd.read_csv('peer-info/previously-shared-with.csv')

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

        return jsonify({
            'peer_pub_key': peer_pub_key
        })
    except Exception as e:
        print(e)


@fi_bp.route('/ui/get-sent-requests', methods=['GET'])
@require_localhost
def get_sent_requests(): 

    try:
        all_requests:pd.DataFrame = pd.read_csv('requests/outgoing.csv')
        if not all_requests.empty:
            all_requests['date'] = pd.to_datetime(all_requests['date'])
            all_requests = all_requests.sort_values(by='date', ascending=False)
        output = all_requests.to_dict(orient='records')
        return jsonify({'all_requests': output})
    except Exception as e:
        print(e)


@fi_bp.route('/ui/get-incoming-requests', methods=['GET'])
@require_localhost
def get_incoming_requests(): 

    try:
        all_requests:pd.DataFrame = pd.read_csv('requests/incoming.csv')
        print(all_requests.head())
        if not all_requests.empty:
            all_requests['date'] = pd.to_datetime(all_requests['date'])
            all_requests = all_requests.sort_values(by='date', ascending=False)
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
        incoming:pd.DataFrame = pd.read_csv('requests/incoming.csv')
        num_incoming = (incoming.size) / 5

        outgoing:pd.DataFrame = pd.read_csv('requests/outgoing.csv')
        num_outgoing = (outgoing.size) / 6

        return jsonify({
            'incoming': num_incoming,
            'outgoing': num_outgoing
        })
    except Exception as e:
        print(e)


@fi_bp.route('/ui/upload-data', methods=['POST'])
@require_localhost
def upload_data(): 
    try:
        peer_pub_key = request.form.get('peer_pub_key', "")
        send_method = request.form.get('send_method', "")
        uploaded_files = request.files.getlist('files')

        for file in uploaded_files:
            file_name = file.filename
            date = datetime.datetime.now()
            fileBytes = file.read()
            size = len(fileBytes)        
            hash_256 = sha256(fileBytes).hexdigest()


        data = [peer_pub_key, file_name, send_method, size, date, hash_256]

        # Open the file in append mode ('a'), create if not exists
        with open('requests/outgoing.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)

        return jsonify({'status': 'success'})    
    except Exception as e:
        print(e)
       
        
@fi_bp.route('/ui/reupload-data', methods=['POST'])
@require_localhost
def reupload_data():
    try:
        incoming_date_key = request.form.get("date", "")

        # Read all rows from the CSV into a list
        with open('requests/outgoing.csv', "r", newline='') as file:
            reader = csv.DictReader(file)
            rows = list(reader)  # Convert to list of dicts
            fieldnames = reader.fieldnames

        # Find the index of the row with the matching date
        index_to_remove = None
        for i, row in enumerate(rows):
            if row["date"] == incoming_date_key:
                index_to_remove = i
                break

        if index_to_remove is not None:
            del rows[index_to_remove]  # Remove the row

        # Overwrite the CSV with only the header (truncate previous data)
        with open('requests/outgoing.csv', 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)  # Re-write all other rows

        # create the new request
        peer_pub_key = request.form.get("peer_pub_key", "")
        file_name = request.form.get("file", "")
        send_method = request.form.get("send_method", "")
        size = request.form.get("size", "")
        new_date = datetime.datetime.now()
        hash_256 = request.form.get("sha256", "")

        data = [peer_pub_key, file_name, send_method, size, new_date, hash_256]

        # add the updated line AND all old lines
        with open('requests/outgoing.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)
#             writer.writerows(rows)

        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error in reupload_data: {e}")
        return jsonify({"error": str(e)})

