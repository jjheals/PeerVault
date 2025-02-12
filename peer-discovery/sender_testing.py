import socket
import struct
import time

MCAST_GRP = "239.255.1.1"   # Multicast group addr
MCAST_PORT = 5001           # Multicast port
IFACE = "192.168.5.115"     # Sender's IP/inferface


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

# Set the network interface for outgoing multicast traffic


# Send messages 
while True:
    message = "Hello, multicast world!"
    sock.sendto(message.encode(), (MCAST_GRP, MCAST_PORT))
    print(f"Sent: {message}")
    time.sleep(2)
