"""
TODO: 
    - in /ui/share-file and /ui/store-file, implement the Server sending a mcast
      msg to find a recipient if the peer_pub_key is blank (empty str)
"""

from flask import Blueprint, jsonify, g, current_app, request, abort, send_file
import os 

from utils import bytes_to_gb, hash_bytes_sha256
from objects import Server, DatabaseConnection

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
            - 404 | not found: if a peer with the given public key is not found. 
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
        
    # Get the app's db connection
    db_connection:DatabaseConnection = current_app.db_connection
    
    # Check if we're finding a recipient or if we were given a public key to send to
    if peer_pub_key: 
        
        # Get the info for this peer
        peer_info:dict = db_connection.peer_info_from_pub_key(peer_pub_key)

        # Check for a match
        if not peer_info or not peer_info.get('most_recent_ip', ''): 
            return jsonify({
                'error': 'No peers found for the given public key.',
                'given_args': {
                    'peer_pub_key': peer_pub_key
                }
            }), 404
    
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
    if not peer_info['online']: 
        
        # Queue the request
        # Create a filepath to a tmp storage dir to save the file
        tmp_filepath:str = os.path.join('requests', 'tmp', filename)
         
        # Save the file to tmp storage 
        with open(tmp_filepath, 'wb') as f:
            f.write(file)
            
        # Add a row to the PendingRequests table
        db_connection.new_pending_request(
            'outgoing',
            'share',
            peer_pub_key,
            os.path.join('requests', 'tmp', filename),
            bytes_to_gb(len(file_content)),
            hash_bytes_sha256(file)
        )

        # Return a status message to the frontend 
        return jsonify({
            'status': 200,
            'message': f'Request to share file with "{peer_info["common_name"]}" is queued for the next time the peer is online.'
        })
    
    # Peer is ONLINE
    else: 
        
        # Send a share request to the peer
        try: 
            
            # Call server.send_share_request() to send the request
            current_app.server.send_share_request(
                peer_info['most_recent_ip'],
                file_content,
                filename
            )
            
            # Notify frontend that the request was successful
            return jsonify({
                'status': 200,
                'message': f'File shared with {peer_info["common_name"]} successfully.'
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

    # Get the app's db connection
    db_connection:DatabaseConnection = current_app.db_connection
    
    # Check if we're finding a recipient or if we were given a public key to send to
    if peer_pub_key: 
        
        # Get the info for this peer
        peer_info:dict = db_connection.peer_info_from_pub_key(peer_pub_key)

        # Check for a match
        if not peer_info or not peer_info.get('most_recent_ip', ''): 
            return jsonify({
                'error': 'No peers found for the given public key.',
                'given_args': {
                    'peer_pub_key': peer_pub_key
                }
            }), 404
    
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
    if not peer_info['online']: 
        
        # Queue the request
        # Create a filepath to a tmp storage dir to save the file
        tmp_filepath:str = os.path.join('requests', 'tmp', filename)
         
        # Save the file to tmp storage 
        with open(tmp_filepath, 'wb') as f:
            f.write(file)
            
        # Add a row to the PendingRequests table
        db_connection.new_pending_request(
            'outgoing',
            'share',
            peer_pub_key,
            os.path.join('requests', 'tmp', filename),
            bytes_to_gb(len(file_content)),
            hash_bytes_sha256(file)
        )

        # Return a status message to the frontend 
        return jsonify({
            'status': 200,
            'message': f'Request to share file with "{peer_info["common_name"]}" is queued for the next time the peer is online.'
        })
    
    # Peer is ONLINE
    else: 
        
        # Send a share request to the peer
        try: 
            
            # Call server.send_share_request() to send the request
            server.send_store_request(
                peer_info["common_name"],
                file_content,
                filename
            )
            
            # Notify frontend that the request was successful
            return jsonify({
                'status': 200,
                'message': f'File stored with {peer_info["common_name"]} successfully.'
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
    if not current_app.server: 
        
        # App is NOT initialized
        print('\033[91mERROR in fe_p2p_bp.delete_file(): \033[0mcurrent app Server is "None", i.e. application has not been initialized')
        return jsonify({'error': "Application backend has not been initialized - use /ui/init-application and provide the user's passcode."}), 400
    
    # App IS initialized
    else: server:Server = current_app.server 
     
    # Get the app's db connection
    db_connection:DatabaseConnection = current_app.db_connection
    
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
    
    # Make sure that this filename is actually currently being stored with the given peer
    if not db_connection.check_stored_with_file_exists(peer_pub_key, filename): 
        return jsonify({
            'error': 'The given peer is not currently storing the given file.',
            'given_args': {
                'peer_pub_key': peer_pub_key,
                'filename': filename
            }
        })
    
    # NOTE: we know the peer_pub_key was given in the request
    # Get the info for this peer
    peer_info:dict = db_connection.peer_info_from_pub_key(peer_pub_key)
    
    # Check that the found peer is online
    # Peer is OFFLINE
    if not peer_info['online']: 

        # Add a row to the PendingRequests table
        db_connection.new_pending_request(
            'outgoing',
            'delete',
            peer_pub_key,
            filename,
            -1,
            ''
        )

        # Return a status message to the frontend 
        return jsonify({
            'status': 200,
            'message': f'Request to share file with "{peer_info["common_name"]}" is queued for the next time the peer is online.'
        })
    
    # Peer is ONLINE
    else: 
        
        # Send a share request to the peer
        try: 
            
            # Get the file hash from the DB
            db_connection.cursor.execute(
                'SELECT sha256 FROM CurrentlyStoringWith WHERE peer_pub_key = ? AND filename = ?', 
                (peer_pub_key, filename)
            )
            
            file_hash:str = db_connection.cursor.fetchone()[0]
            
            # Call server.send_delete_request() to send the request
            server.send_delete_request(
                peer_pub_key,
                peer_info['most_recent_ip'],
                filename,
                file_hash=file_hash
            )
            
            # Notify frontend that the request was successful
            return jsonify({
                'status': 200,
                'message': f'File "{filename}" deleted from {peer_info["common_name"]} successfully.'
            })
        
        except Exception as e: 
            print(f'\033[91mERROR in fi_bp.store_file(): \033[0mthere was an error sending the delete request for file "{filename}" to peer "{peer_cn}". Exception: ', e)
            return jsonify({'error': 'An error occured during file store request. Error: ' + str(e)}), 500
            

@fe_p2p_bp.route('/ui/retrieve-stored-file', methods=['GET'])
@require_localhost
def retrieve_stored_file(): 
    """
        DESC: sends a request to the given peer to retrieve the contents of the given filename.

        ARGUMENTS: 
            peer_pub_key (str): the public key of the peer storing the file.
            filename (str): the filename to retrieve.
        
        RETURNS: 
            - 200 | successful: (blob) the requested file.
            - 400 | bad request: if the user fails to supply the required data OR if the provided data is invalid, or if the server is not initialized.
            - 403 | unauthorized: if the request comes from a non-loopback address (not localhost).
            - 404 | not found: if there is an error from the peer processing the request, which likely means they did not find the file.
            - 406 | not acceptable: if a peer with the given public key is not found OR the given peer is not storing the given filename. 
            - 500 | internal server error: if there is some error in processing the request.
    """
    
    # Make sure server is initialized
    server:Server = current_app.server
    if not server: abort(400)

    # Get the app's db connection
    db_connection:DatabaseConnection = current_app.db_connection
    
    # Extract the arguments from the request 
    peer_pub_key:str = request.args.get('peer_pub_key', None)
    filename:str = request.args.get('filename', None)

    # Verify that the required args were given
    if not (peer_pub_key and filename): 
        return jsonify({
            'error': 'Missing required arguments.',
            'given_args': {
                'peer_pub_key': peer_pub_key,
                'filename': filename
            }
        }), 400
    
    # Make sure that this filename is actually currently being stored with the given peer
    if not db_connection.check_stored_with_file_exists(peer_pub_key, filename): 
        return jsonify({
            'error': 'The given peer is not currently storing the given file.',
            'given_args': {
                'peer_pub_key': peer_pub_key,
                'filename': filename
            }
        })

    # Get the info for this peer
    peer_info:dict = db_connection.peer_info_from_pub_key(peer_pub_key)
    
    # Get the most recent IP and online status if a match was found
    if peer_info and peer_info['most_recent_ip']:
        peer_ip:str = peer_info['most_recent_ip']
        peer_online_status:bool = peer_info['online']    
        peer_cn:str = peer_info['common_name']            # NOTE: peer common name is only used for returning a status message
    
    # No matches mean that the peer doesn't exist 
    else:
        return jsonify({
            'error': 'There is no peer with the given public key.',
            'given_args': {
                'peer_pub_key': peer_pub_key,
                'filename': filename
            }
        })
    
    # Check if the peer is online 
    # Peer is ONLINE
    if peer_online_status:
        
        # Send the request to retrieve the file
        try: 
            tmp_file_path:str = server.retrieve_stored_file(
                peer_pub_key,
                peer_ip,
                filename,
                current_app.identity_config['PATHS']['tmp_storage_path']
            )

            # Check if we got something back
            if not tmp_file_path: raise Exception('The peer did not return any file contents.')

        # Handle exceptions 
        except Exception as e: 
            return jsonify({
                'error': 'An error occured while the peer was processing the request',
                'message': f'{e.__class__} - {e}'
            })
        
        # Send the file back to the frontend
        return send_file(
            tmp_file_path,          
            as_attachment=True  # Force download prompt
        )
        
    # Peer is OFFLINE
    else: 

        # Get the file hash from the DB
        db_connection.cursor.execute(
            'SELECT sha256 FROM CurrentlyStoringWith WHERE peer_pub_key = ? AND filename = ?', 
            (peer_pub_key, filename)
        )
        
        file_hash:str = db_connection.cursor.fetchone()[0]
        
        # Add a row to the PendingRequests table
        db_connection.new_pending_request(
            'outgoing', 
            'retrieve',
            peer_pub_key,
            filename,
            -1,
            file_hash
        )

        # Return a status message to the frontend 
        return jsonify({
            'status': 200,
            'message': f'Request to retrieve file from "{peer_cn}" is queued for the next time the peer is online.'
        })