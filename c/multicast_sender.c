#define _DEFAULT_SOURCE  // Ensure necessary networking features are available

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32  // Windows-specific includes
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")  // Link Winsock library
#else  // Linux-specific includes
    #include <arpa/inet.h>
    #include <sys/types.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <unistd.h>
#endif

#define MCAST_GROUP "239.255.1.1"
#define MCAST_PORT 5001

int main() {

    // Init sockets
    int sock;
    struct sockaddr_in mcastAddr;
    
    
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

    // Set multicast TTL (Time-to-Live)
    int ttl = 2;
    if (setsockopt(sock, IPPROTO_IP, IP_MULTICAST_TTL, (char *)&ttl, sizeof(ttl)) < 0) {
        perror("Setting IP_MULTICAST_TTL failed");
        exit(1);
    }

    // Configure multicast address
    memset(&mcastAddr, 0, sizeof(mcastAddr));
    mcastAddr.sin_family = AF_INET;
    mcastAddr.sin_addr.s_addr = inet_addr(MCAST_GROUP);
    mcastAddr.sin_port = htons(MCAST_PORT);

    // Set up base messages
    int count = 0;
    char* message = "Hello from multicast sender!";

    while (1) {
        // Determine required buffer size for new message
        int size = snprintf(NULL, 0, "%s (%d)", message, count++) + 1;

        // Allocate memory for the new message
        char* formatted_message = (char*) malloc(size);
         
        // Check for failure 
        if (formatted_message == NULL) {
            perror("Memory allocation failed");
            continue;
        }

        // Format the message and point to formatted_message
        snprintf(formatted_message, size, "%s (%d)", message, count);
       
        // Send message to multicast group
        if (sendto(sock, formatted_message, strlen(formatted_message), 0, (struct sockaddr*)&mcastAddr, sizeof(mcastAddr)) < 0) {
            perror("Sending multicast message failed");
            exit(1);
        }

        printf("Sent multicast message: %s\n", formatted_message);
        
        #ifdef _WIN32
            Sleep(5000);
        #else
            sleep(5);
        #endif
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
