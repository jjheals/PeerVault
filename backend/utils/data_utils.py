import csv 
import pandas as pd 


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

