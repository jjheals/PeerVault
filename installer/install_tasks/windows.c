#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "windows.h"
#include "colors.h"


int windows_install() {
    printf(BOLD_YELLOW "\n[Windows] Installing files...\n" RESET);

    // Define relative paths 
    char* venv_path = "..\\backend\\venv";
    char* activate_venv_path = "..\\backend\\venv\\Scripts\\activate";
    char* requirements_txt_path = "..\\backend\\refs\\requirements.txt";
    char* pip_path = "..\\backend\\venv\\Scripts\\pip";
    
    // Define buff for building command strings
    char command[512]; 

    // Step 1: Create a virtual environment
    printf(BOLD_WHITE "[+] Creating Python virtual environment...\n" RESET);

    // Clear the buffer
    command[0] = '\0';

    // Strcat the cmd to create a python venv -> command, then strcat the venv path onto that
    strcat(command, "python -m venv ");
    strcat(command, venv_path);

    // Debug print
    printf(BOLD_WHITE "[+] Running command: %s\n" RESET, command);
    
    // Run the command
    int venv_result = system(command);

    // Handle result
    if (venv_result != 0) {
        printf(BOLD_RED "ERROR: " RESET "Failed to create virtual environment.\n");
        return 0; // failure
    }

    // Step 2: Install requirements
    // Activate the venv 
    printf(BOLD_WHITE "[+] Activating venv." RESET);
    system(activate_venv_path);

    printf(BOLD_WHITE "[+] Installing Python dependencies...\n" RESET);

    // Clear the buffer
    command[0] = '\0';

    // Strcat the pip path -> command, then strcat the static str for install -r, then strcat the requirements.txt path
    strcat(command, pip_path);
    strcat(command, " install -r ");
    strcat(command, requirements_txt_path);

    // Debug print
    printf(BOLD_WHITE "[+] Running command: %s\n" RESET, command);

    // Run the pip installl command 
    int pip_result = system(command);

    // Handle result
    if (pip_result != 0) {
        printf(BOLD_RED "ERROR: " RESET "Failed to install Python dependencies.\n");
        return 0; // failure
    }

    printf(BOLD_GREEN "[+] SUCCESS: " RESET "Python environment and dependencies installed successfully.\n");
    return 1; // success
}

