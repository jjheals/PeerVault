import socket 
import struct 
import json


def join_multicast(mcast_group:str, mcast_port:int, local_ip:str) -> None:
    """Listens for multicast messages from peers.
    
        ARGS: 
            :str mcast_group - the multicast address to listen on
            :int mcast_port - the local port to bind the listener to

        RETURNS: 
            :None - binds a listener to the given [mcast_port] and subscribes to the given [mcast_group]
    """

    # Init socket cxn
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind to the multicast port
    sock.bind((local_ip, mcast_port))

    # Construct a message to send to the multicast group
    mcast_req:bytes = struct.pack(
        "4sl", 
        socket.inet_aton(mcast_group), 
        socket.INADDR_ANY
    )

    # Send the multicast message to the group
    sock.setsockopt(
        socket.IPPROTO_IP, 
        socket.IP_ADD_MEMBERSHIP, 
        mcast_req
    )

    # Listen for incoming messages
    print("[Multicast Listener] Listening for peer announcements...")

    while True:
        data, addr = sock.recvfrom(1024)  # Receive message
        peer_info = json.loads(data.decode())

        print(f"[Listener] New peer discovered: {peer_info}")

        # TODO: Update peer settings in local network graph
        # DO SOMETHING ...
        # ...
