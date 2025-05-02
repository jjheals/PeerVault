# --- Config vars --- #
CC = gcc
TARGET = PeerVault

# Source and object files shared across platforms
COMMON_SRCS = utils/misc.c
COMMON_OBJS = $(COMMON_SRCS:.c=.o)

# Flags
CFLAGS = -Wall -Wextra -std=c11 -Iinstall_tasks -Iinclude -v

# --- Platform-specific setup --- #
ifeq ($(OS),Windows_NT)
    PLATFORM_SRC = PeerVault_windows.c utils/windows.c
    PLATFORM_OBJS = $(PLATFORM_SRC:.c=.o)
    EXECUTABLE = ..\\$(TARGET).exe
    RM = del /Q
else
    PLATFORM_SRC = PeerVault_unix.c utils/unix.c
    PLATFORM_OBJS = $(PLATFORM_SRC:.c=.o)
    EXECUTABLE = ../$(TARGET)
    RM = rm -f
endif

# All object files to compile
OBJS = $(COMMON_OBJS) $(PLATFORM_OBJS)

# --- Targets --- #
all: $(EXECUTABLE)

$(EXECUTABLE): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $(OBJS)
	$(MAKE) clean-obj

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# --- Extra rules --- #
clean-obj:
ifeq ($(OS),Windows_NT)
	-$(RM) *.o 2>nul || exit 0
	-$(RM) utils\\*.o 2>nul || exit 0
else
	-find . -name "*.o" -exec rm -f {} +
endif

clean:
ifeq ($(OS),Windows_NT)
	-$(RM) $(EXECUTABLE) 2>nul || exit 0
	-$(RM) *.o 2>nul || exit 0
	-$(RM) utils\\*.o 2>nul || exit 0
else
	-rm -f $(EXECUTABLE)
	-find . -name "*.o" -exec rm -f {} +
endif
