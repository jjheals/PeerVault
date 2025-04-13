import json
from flask import Blueprint, jsonify, g, current_app, request, abort
import os 
import pandas as pd
import numpy as np 
from configparser import ConfigParser
from hashlib import sha256
import csv
import pandas as pd

from utils import filter_args, load_key_pem, get_mac_address, getCommonNameFromPubKey, getPubKeyFromCommonName, getUniquePeers, now, generate_asymm_keys
from objects import Server 

from .funcs import require_localhost
from werkzeug.utils import secure_filename

# ---- Config & init ---- #
# Create blueprint
fe_p2p_bp:Blueprint = Blueprint('frontend_p2p', __name__)


# --- Endpoints ---- #

@fe_p2p_bp.route('/ui/share-file', methods=['POST'])
@require_localhost
def share_file(): 
    """
        DESC: Initaites a share request with a peer. 
        
        REQ BODY: 
            The request body should be form data (JS obj FormData). There should also be a file attached to the 
            request - in JS do this with: 
                
                ```javascript
                    const formData = new FormData();
                    formData.append('file', selectedFile);
                    formData.append('peer_pub_key': '<PUBLIC KEY>')
                    
                    // Use formData as the request body ... 
                    // ... 
                ```
            
            NOTE: 
                - If the peer_pub_key is empty string, then the server will initiate a broadcast message to find 
                a recipient that is online.
        
        RETURNS: 
            - 200 | successful: (dict) a JSON object that contains the info of the peer that the file was sent to (or is pending to be sent to) 
            - 400 | bad request: if the user fails to supply the required data OR if the provided data is invalid.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 406 | not acceptable: if a peer with the given public key is not found. 
            - 500 | internal server error: if there is some error in processing the request.
    """
    
    # NOTE: check that current_app.server is not None 
    if not current_app.server: 
        print('\033[91mERROR in fe_p2p_bp.share_file(): \033[0mcurrent app Server is "None", i.e. application has not been initialized')
        return jsonify({'error': "Application backend has not been initialized - use /ui/init-application and provide the user's passcode."}), 400
     
    # Extract req body
    request_json:dict = request.form.to_dict()
    
    # Extract data from req body
    try: 
        peer_pub_key:str = request_json['peer_pub_key']
        file:bytes = request.files['file']
        
    # Exception means a key error or something else was wrong about the request 
    except Exception as e: 
        print('\033[91mERROR in fe_p2p_bp.share_file(): \033[0m', e)
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
            peer_cn:str = row.iloc[0]['common_name']            # NOTE: peer common name is only used for returning a status message
        else: 
            # No match was found, return HTTP 406 (Not Acceptable) 
            abort(406)
    
    # Find a recipient using multicast
    else: 
        # TODO: implement multicast message to find a recipient
        # DO SOMETHING ... 
        return jsonify({
            'status': 200, 
            'message': 'Implementation for finding a recipient is not complete.'
        })

    # Check that the found peer is online
    # Peer is OFFLINE
    if not peer_online_status: 
        
        # TODO: queue the request using some persistent storage (i.e. to disk) to send for when the peer is online
        # DO SOMETHING ... 
        # ...

        return jsonify({
            'status': 500,
            'message': 'Peer is offline and message queue functionality is not complete.'
        })
    
    # Peer is ONLINE
    else: 
        
        # Send a share request to the peer
        try: 
            
            # Call server.send_share_request() to send the request
            current_app.server.send_share_request(
                peer_ip,
                file_content,
                filename
            )
            
            # Notify frontend that the request was successful
            return jsonify({
                'status': 200,
                'message': f'File shared with {peer_cn} successfully.'
            })
        
        except Exception as e: 
            print('\033[91mERROR in fi_bp.send_file(): \033[0mthere was an error sending the file. Exception: ', e)
            return jsonify({'error': 'An error occured during file share request. Error: ' + str(e)}), 500
            
            
@fe_p2p_bp.route('/ui/store-file', methods=['POST'])
@require_localhost
def store_file(): 
    """
        DESC: Initaites a store request with a peer. 
        
        REQ BODY: 
            The request body should be form data (JS obj FormData). There should also be a file attached to the 
            request - in JS do this with: 
                
                ```javascript
                    const formData = new FormData();
                    formData.append('file', selectedFile);
                    formData.append('peer_pub_key': '<PUBLIC KEY>')
                    
                    // Use formData as the request body ... 
                    // ... 
                ```
            
            NOTE: 
                - If the peer_pub_key is empty string, then the server will initiate a broadcast message to find 
                a recipient that is online.
        
        RETURNS: 
            - 200 | successful: (dict) a JSON object that contains the info of the peer that the file was stored with (or is pending to be stored with) 
            - 400 | bad request: if the user fails to supply the required data OR if the provided data is invalid.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 406 | not acceptable: if a peer with the given public key is not found. 
            - 500 | internal server error: if there is some error in processing the request.
    """
    
    # NOTE: check that current_app.server is not None 
    # App is NOT initialized
    if not current_app.server: 
        print('\033[91mERROR in fe_p2p_bp.store_file(): \033[0mcurrent app Server is "None", i.e. application has not been initialized')
        return jsonify({'error': "Application backend has not been initialized - use /ui/init-application and provide the user's passcode."}), 400
    
    # App IS initialized
    else: server:Server = current_app.server 
     
    # Extract req body
    request_json:dict = request.form.to_dict()
    
    # Extract data from req body
    try: 
        peer_pub_key:str = request_json['peer_pub_key']
        file:bytes = request.files['file']
        
    # Exception means a key error or something else was wrong about the request 
    except Exception as e: 
        print('\033[91mERROR in fe_p2p_bp.store_file(): \033[0m', e)
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
            peer_cn:str = row.iloc[0]['common_name']            # NOTE: peer common name is only used for returning a status message
        else: 
            # No match was found, return HTTP 406 (Not Acceptable) 
            abort(406)
    
    # Find a recipient using multicast
    else: 
        # TODO: implement multicast message to find a recipient
        # DO SOMETHING ... 
        return jsonify({
            'status': 200, 
            'message': 'Implementation for finding a recipient is not complete.'
        })

    # Check that the found peer is online
    # Peer is OFFLINE
    if not peer_online_status: 
        
        # TODO: queue the request using some persistent storage (i.e. to disk) to send for when the peer is online
        # DO SOMETHING ... 
        # ...

        return jsonify({
            'status': 500,
            'message': 'Peer is offline and message queue functionality is not complete.'
        })
    
    # Peer is ONLINE
    else: 
        
        # Send a share request to the peer
        try: 
            
            # Call server.send_share_request() to send the request
            server.send_store_request(
                peer_ip,
                file_content,
                filename
            )
            
            # Notify frontend that the request was successful
            return jsonify({
                'status': 200,
                'message': f'File stored with {peer_cn} successfully.'
            })
        
        except Exception as e: 
            print('\033[91mERROR in fi_bp.store_file(): \033[0mthere was an error sending the file to be stored. Exception: ', e)
            return jsonify({'error': 'An error occured during file store request. Error: ' + str(e)}), 500
            

@fe_p2p_bp.route('/ui/delete-file', methods=['POST'])
@require_localhost
def delete_file(): 
    """
        DESC: Initaites a delete request with a peer. 
        
        REQ BODY: 
            The request body should be form data (JS obj FormData). There should also be a file attached to the 
            request - in JS do this with: 
                
                ```javascript
                    const formData = new FormData();
                    formData.append('filename', selectedFilename);
                    formData.append('peer_pub_key': '<PUBLIC KEY>')
                    
                    // Use formData as the request body ... 
                    // ... 
                ```
            
            NOTE: 
                - If the peer_pub_key is empty string, then the server will initiate a broadcast message to find 
                a recipient that is online.
        
        RETURNS: 
            - 200 | successful: (dict) a JSON object that contains the info of the peer that the file was deleted from (or is pending to be deleted from) 
            - 400 | bad request: if the user fails to supply the required data OR if the provided data is invalid.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 406 | not acceptable: if a peer with the given public key is not found. 
            - 500 | internal server error: if there is some error in processing the request.
    """
    
    # NOTE: check that current_app.server is not None 
    # App is NOT initialized
    if not current_app.server: 
        print('\033[91mERROR in fe_p2p_bp.delete_file(): \033[0mcurrent app Server is "None", i.e. application has not been initialized')
        return jsonify({'error': "Application backend has not been initialized - use /ui/init-application and provide the user's passcode."}), 400
    
    # App IS initialized
    else: server:Server = current_app.server 
     
    # Extract req body
    request_json:dict = request.form.to_dict()
    
    # Extract data from req body
    try: 
        peer_pub_key:str = request_json['peer_pub_key']
        filename:bytes = request_json['filename']
        
        # Make sure a peer pub key was given 
        if not peer_pub_key: raise Exception('A peer_pub_key is required for DELETE requests.')
        
    # Exception means a key error or something else was wrong about the request 
    except Exception as e: 
        print('\033[91mERROR in fe_p2p_bp.delete_file(): \033[0m', e)
        abort(400)
    
    # Init vars for the peer's IP and online status
    peer_ip:str = None
    peer_online_status:bool = None

    # NOTE: we know the peer_pub_key was given in the request
    # Load the all peers df so we can convert the public key to an IP address
    all_peers_df:pd.DataFrame = pd.read_csv('peer-info/all-peers.csv')
    
    # Get the row that matches this public key
    row:np.ndarray = all_peers_df.loc[all_peers_df['peer_pub_key'] == peer_pub_key]
    
    # Get the most recent IP, online status, and hash if a match was found
    if row and not row.empty:
        peer_ip:str = row.iloc[0]['most_recent_ip']
        peer_online_status:bool = row.iloc[0]['online']    
        file_hash:str = row.iloc[0]['sha256']
        peer_cn:str = row.iloc[0]['common_name']            # NOTE: peer common name is only used for returning a status message
    else: 
        # No match was found, return HTTP 406 (Not Acceptable) 
        abort(406)
    
    # Make sure that this filename is actually currently being stored with the given peer
    stored_with_df:pd.DataFrame = pd.read_csv('peer-info/currently-storing-with.csv')
    
    # Check that a row exists for this filename and this peer_pub_key
    matched_row:pd.DataFrame = stored_with_df.loc[stored_with_df[['peer_pub_key', 'filename']] == [peer_pub_key, filename]] 
    
    # Make sure a match was found
    if not matched_row: 
        print(f'\033[91mERROR in fe_p2p_bp.delete_file(): \033[0mthere is no file named "{filename}" currently being stored with the peer "{peer_cn}".')
        return jsonify({
            'status': 406,
            'message': f'There is no file named "{filename}" currently being stored with the peer "{peer_cn}".'
        })
        
    # Check that the found peer is online
    # Peer is OFFLINE
    if not peer_online_status: 
        
        # TODO: queue the request using some persistent storage (i.e. to disk) to send for when the peer is online
        # DO SOMETHING ... 
        # ...

        return jsonify({
            'status': 500,
            'message': 'Peer is offline and message queue functionality is not complete.'
        })
    
    # Peer is ONLINE
    else: 
        
        # Send a share request to the peer
        try: 
            
            # Call server.send_share_request() to send the request
            server.send_delete_request(
                peer_ip,
                filename,
                file_hash
            )
            
            # Notify frontend that the request was successful
            return jsonify({
                'status': 200,
                'message': f'File "{filename}" deleted from {peer_cn} successfully.'
            })
        
        except Exception as e: 
            print(f'\033[91mERROR in fi_bp.store_file(): \033[0mthere was an error sending the delete request for file "{filename}" to peer "{peer_cn}". Exception: ', e)
            return jsonify({'error': 'An error occured during file store request. Error: ' + str(e)}), 500
            
            