# Cross-Compiler for Windows
CC = x86_64-w64-mingw32-gcc  # Use MinGW-w64 to create Windows executables

# Compiler flags
CFLAGS = -Wall -Wextra -std=c99

# Windows-specific linker flags
LDFLAGS = -lws2_32  # Link Winsock2 for Windows networking

# Source files
SRCS = multicast_listener.c multicast_sender.c

# Output executables
TARGETS = multicast_listener.exe multicast_sender.exe

# Default rule: Build both executables
all: $(TARGETS)

# Compile multicast_listener for Windows
multicast_listener.exe: multicast_listener.c
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

# Compile multicast_sender for Windows
multicast_sender.exe: multicast_sender.c
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

# Clean: Remove generated files
clean:
	rm -f multicast_listener.exe multicast_sender.exe
