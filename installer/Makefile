
# --- Config vars --- #
# Compiler (gcc or clang)
CC = gcc

# Target filename 
TARGET = installer

# Object files
OBJS = main.o installer.o

# NOTE: 
# - Wall => enable all important warnings
# - Wextra => even more warnings
# -std=c11 => use C11 (modern C)
# -Iinstall_tasks => folder to look for header files
# -v => verbose outputs
CFLAGS = -Wall -Wextra -std=c11 -Iinstall_tasks -v

# --- Compile based on platform --- #
# WINDOWS
ifeq ($(OS),Windows_NT)
    OBJS += install_tasks/windows.o
    RM = del /Q	
	EXECUTABLE = $(TARGET).exe
	DIR_DELIM = \\ 

# LINUX/UNIX
else
    OBJS += install_tasks/unix.o		
	RM = rm -f
	EXECUTABLE = $(TARGET)
	DIR_DELIM = /
endif

# --- Define targets --- #
# all => default target 
all: $(EXECUTABLE)		

# --- Build --- #
# Compile obj files
$(EXECUTABLE): $(OBJS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS)
	$(MAKE) clean-obj 
	
# Compile executable
# NOTE: "%.o: %.c" => "for any .o file where there is a matching .c file" 
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@
	
# --- Extra rules --- #
clean-obj:
ifeq ($(OS),Windows_NT)
	-$(RM) *.o 2>nul || exit 0
	-$(RM) install_tasks\\*.o 2>nul || exit 0
else
	-find . -name "*.o" -exec rm -f {} +
endif

# Clean rule
clean:
ifeq ($(OS),Windows_NT)
	-$(RM) $(EXECUTABLE) 2>nul || exit 0
	-$(RM) *.o 2>nul || exit 0
	-$(RM) install_tasks\\*.o 2>nul || exit 0
else
	-rm -f $(EXECUTABLE)
	-find . -name "*.o" -exec rm -f {} +
endif

