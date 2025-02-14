import socket
import time
from configparser import ConfigParser
from utils import load_key
import json 


# --- Load config --- #
config:ConfigParser = ConfigParser()
config.read('config/multicast-config.conf')

MCAST_GRP = config['multicast-config']['MCAST_GROUP']       # Multicast group addr
MCAST_PORT = int(config['multicast-config']['MCAST_PORT'])  # Port to listen on
IFACE = config['multicast-config']['LOCAL_IP']              # Local IP

# Create the socket
sock = socket.socket(
    socket.AF_INET,         # Specify IPv4
    socket.SOCK_DGRAM,      # UDP socket
    socket.IPPROTO_UDP      # UDP protocol 
)

# Set the TTL
sock.setsockopt(
    socket.IPPROTO_IP,          # Modifying an IP-level setting
    socket.IP_MULTICAST_TTL,    # Setting the mcast TTL
    2                           # TTL
)


# Send a multicast message with this machine's common name, IP, and pub key
while True:
    
    # Get this user's common name
    with open('config/local_config.json', 'r') as file: 
        common_name:str = json.load(file)['common_name']
    
    # Load the public key
    pub_key_str:str = load_key('keys/public.key', 'public') 
    
    message:dict = {
        'public_key': pub_key_str,
        'ip': IFACE,
        'common_name': common_name
    }
    
    # Send the message to the multicast group
    sock.sendto(json.dumps(message).encode(), (MCAST_GRP, MCAST_PORT))
    
    
    print(f"Sent: {message}")
    time.sleep(2)
