import csv 
import pandas as pd 

import pandas as pd 
from .enc_utils import strip_pem_headers


def update_peer_info(peer_public_key:str, csv_path:str, peer_info:dict[str, str|bool]) -> None: 
    """Takes in a public key and path to the all-peers.csv file, and updates the info for the given public key in the 
    given CSV.
    
    Args: 
        peer_public_key (str): the public key of the peer to update (no PEM headers).
        csv_path (str): path to the all-peers.csv file to update. 
        peer_info (dict[str, str|int]): info of new info for this peer (note: pub key will not be changed).
        
    NOTE: 
        - if the peer HAS been seen before (i.e. there is already an entry for this public key), then only the "most_recent_ip"
          and "online" will be updated. In this case, the peer_info dict must only contain at least: 
            - peer_status: <bool> (online/True | offline/False)
            - peer_ip: <str> 
            
        - if the peer HAS NOT been seen before (i.e. there is not already an entry for this public key), then a new entry will
          be created for this peer, and the peer_info must include all of:
            - peer_status: <bool> (online/True | offline/False)
            - peer_ip: <str> 
            - peer_common_name: <str> 
            - peer_mac_last_four: <str> 
    """
    
    # Update the all-peers info with the new IP for this peer and set their status to ONLINE
    # Read the existing all_peers_df
    all_peers_df:pd.DataFrame = pd.read_csv(csv_path)
    
    # Strip the header and footer from the peer's public key pem and remove quotes and newlines (incase this wasn't already done)
    peer_pub_key_str:str = strip_pem_headers(peer_public_key).replace('"', '').replace('\n', '')
    
    # Check if the peer public key exists already
    peer_exists:bool = len(all_peers_df.loc[all_peers_df['peer_pub_key'] == peer_pub_key_str])
    
    # Handle if the peer exists already or not
    if peer_exists: 
        
        # Update the row in the df with the new IP for this peer and mark them as ONLINE
        all_peers_df.loc[all_peers_df['peer_pub_key'] == peer_pub_key_str, ['most_recent_ip', 'online']] = [peer_info['peer_ip'], peer_info['peer_status']]

    else: 
        # Peer doesn't exist, so make an entry for them
        new_entry:dict = {
            'peer_pub_key': peer_pub_key_str, 
            'online': peer_info['peer_status'],
            'most_recent_ip': peer_info['peer_ip'],
            'common_name': peer_info['peer_common_name'],
            'mac_last_four': peer_info['peer_mac_last_four']
        }
        
        # Append the entry to the all peers df
        all_peers_df = pd.concat([all_peers_df, pd.DataFrame([new_entry])], ignore_index=True)
    
    # Resave the all_peers_df
    all_peers_df.to_csv(csv_path, index=False)
    
    
def getCommonNameFromPubKey(pub_key: str):
    with open('peer-info/all-peers.csv', 'r', newline='') as f:
        reader = csv.reader(f)
        next(reader, None)

        for row in reader:
            if row[0] == pub_key:
                return row[3] 
            

def getPubKeyFromCommonName(common_name: str):
    all_peers = pd.read_csv('peer-info/all-peers.csv')
    result = all_peers[all_peers['common_name'] == common_name]['peer_pub_key']
    return result.iloc[0] if not result.empty else None


def getUniquePeers() -> list:
    storing_for_df = pd.read_csv('peer-info/currently-storing-for.csv')
    storing_with_df = pd.read_csv('peer-info/currently-storing-with.csv')
    shared_with_df = pd.read_csv('peer-info/previously-shared-with.csv')

    data = pd.concat([storing_for_df, storing_with_df, shared_with_df], ignore_index=True)

    unique_peers = data['peer_pub_key'].unique()
    
    return unique_peers.tolist()

