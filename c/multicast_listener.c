#define _DEFAULT_SOURCE  // Ensure ip_mreq is available
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Windows-specific includes
#ifdef _WIN32  
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")  // Link Winsock library

// Linux-specific includes
#else  
    #include <arpa/inet.h>
    #include <sys/types.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <unistd.h>
#endif

#define MCAST_GROUP "239.255.1.1"
#define MCAST_PORT 5001

int main() {
    int sock;
    struct sockaddr_in localAddr;
    struct ip_mreq mreq;
    char buffer[1024];
    ssize_t bytesReceived;
    socklen_t addrLen = sizeof(localAddr);

    #ifdef _WIN32
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            printf("WSAStartup failed!\n");
            return 1;
        }
    #endif

    // Create UDP socket
    if ((sock = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Socket creation failed");
        exit(1);
    }

    // Allow multiple sockets to use the same port
    int reuse = 1;
    if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
        perror("Setting SO_REUSEADDR failed");
        exit(1);
    }

    // Bind to multicast port
    memset(&localAddr, 0, sizeof(localAddr));
    localAddr.sin_family = AF_INET;
    localAddr.sin_addr.s_addr = INADDR_ANY;
    localAddr.sin_port = htons(MCAST_PORT);

    if (bind(sock, (struct sockaddr*)&localAddr, sizeof(localAddr)) < 0) {
        perror("Binding failed");
        exit(1);
    }

    // Init struct
    memset(&mreq, 0, sizeof(mreq));

    // Specify multicast group
    mreq.imr_multiaddr.s_addr = inet_addr(MCAST_GROUP);
    mreq.imr_interface.s_addr = htonl(INADDR_ANY);

    // Join the multicast group
    if (setsockopt(sock, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq, sizeof(mreq)) < 0) {
        perror("Joining multicast group failed");
        exit(1);
    }

    // Debug message
    printf("Listening for multicast messages on %s:%d...\n", MCAST_GROUP, MCAST_PORT);

    // Listen until program quits
    while (1) {
        bytesReceived = recvfrom(sock, buffer, sizeof(buffer) - 1, 0, (struct sockaddr*)&localAddr, &addrLen);
        if (bytesReceived < 0) {
            perror("Receiving failed");
            continue;
        }

        buffer[bytesReceived] = '\0';
        printf("Received: %s\n", buffer);
    }

    // Cleanup
    #ifdef _WIN32
        closesocket(sock);
        WSACleanup();
    #else
        close(sock);
    #endif

    return 0;
}
