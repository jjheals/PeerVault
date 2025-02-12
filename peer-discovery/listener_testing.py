import socket
import struct
import json 
from configparser import ConfigParser


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

# Enable address reuse 
sock.setsockopt(
    socket.SOL_SOCKET,      # Apply to the socket 
    socket.SO_REUSEADDR,    # Allow multiple sockets to bind to the same port
    1                       # 1 = enable, 0 = disable
)

# Bind the socket to the correct interface and port
sock.bind((IFACE, MCAST_PORT))

# Pack group and interface together 
mreq = struct.pack( 
    "4s4s",                         # Pack format 
    socket.inet_aton(MCAST_GRP),    # Convert mcast group addr to binary
    socket.inet_aton(IFACE)         # Convert local interface/addr to binary
)

sock.setsockopt(
    socket.IPPROTO_IP,          # Modifying an IP-level setting 
    socket.IP_ADD_MEMBERSHIP,   # Join multicast group
    mreq                        # Group & local interface pack
)

# Listen for incoming messages
print("[Multicast Listener] Listening for peer announcements...")

while True:
    data, addr = sock.recvfrom(1024)  # Receive message
    peer_info = data.decode()

    print(f"[Listener] New peer discovered: {peer_info}")