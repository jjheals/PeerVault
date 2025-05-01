#include <stdio.h>
#include <stdlib.h>
#include <string.h>              // For strcat()
#include <windows.h>             // For CreateProcess(), ZeroMemory, etc.
#include <time.h>                // For sleep()
#include "windows_tasks.h"       // For func declarations
#include "colors.h"              // For printing colors


// --- Path variable definitions --- //
// Backend paths
const char* venv_path = "..\\backend\\venv";
const char* activate_venv_path = "..\\backend\\venv\\Scripts\\activate";
const char* requirements_txt_path = "..\\backend\\refs\\requirements.txt";
const char* pip_path = "..\\backend\\venv\\Scripts\\pip";
const char* pip_output_str = "> pip_output.log 2>&1";

// Frontend paths
const char* frontend_dir = "..\\frontend";
const char* npm_install_output_str = "> npm_install_output.log 2>&1";
const char* npm_build_output_str = "> npm_build_output.log 2>&1";


/** spinner_progress_printer(command)
 * @brief Executes the given command and prints a spinner while executing. 
 * @param command the command to execute.
 * @return An integer, 1 if the command succeeds and 0 if it fails. 
 */
int spinner_progress_printer(char* command) {

    // Init vars 
    STARTUPINFO si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    // Start the child process
    if (!CreateProcess(
        NULL,               // No module name (use command line)
        command,            // Command line
        NULL,               // Process handle not inheritable
        NULL,               // Thread handle not inheritable
        FALSE,              // Set handle inheritance to FALSE
        CREATE_NO_WINDOW,   // Don't create new window
        NULL,               // Use parent's environment block
        NULL,               // Use parent's starting directory 
        &si,                // Pointer to STARTUPINFO structure
        &pi)                // Pointer to PROCESS_INFORMATION structure
    ) {
        return 0;
    }

    // Spinner while waiting
    const char spinner[] = "|/-\\";
    int spinner_index = 0;

    // Wait while command executes
    while (1) {

        // Check every 100ms
        DWORD result = WaitForSingleObject(pi.hProcess, 100); 

        // Print spinner 
        printf("\b%c", spinner[spinner_index]);
        fflush(stdout);

        // Increase idx 
        spinner_index = (spinner_index + 1) % 4;

        // Check process finished
        if (result == WAIT_OBJECT_0) {
            
            // Clear terminal for newlines
            printf("\b \b");   // Erase spinner
            printf("\n");      // Newline
            fflush(stdout);    // Flush output

            // Exit loop
            break;
        }
    }

    // Return True
    return 1;
}


int windows_install() {
    printf(BOLD_YELLOW "\n[Windows] Installing files...\n" RESET);

    // Define buff for building command strings
    char command[512]; 

    // --- Create a virtual environment --- //
    // Info print
    printf(BOLD_WHITE "[+] Creating Python virtual environment...\n" RESET);

    // Clear the buffer
    command[0] = '\0';

    // Strcat the cmd to create a python venv -> command, then strcat the venv path onto that
    strcat(command, "python -m venv ");
    strcat(command, venv_path);
    
    // Run the command
    int venv_result = spinner_progress_printer(command);

    // Handle result
    if (venv_result == 0) {
        printf(BOLD_RED "ERROR: " RESET "Failed to create virtual environment.\n");
        return 0; // failure
    }

    // --- Install requirements --- //
    // Activate the venv 
    system(activate_venv_path);
    printf(BOLD_WHITE "[+] Activated venv.\n" RESET);
    
    // Info print
    printf(BOLD_WHITE "[+] Installing Python dependencies via pip...\n" RESET);

    // Create the pip install command
    command[0] = '\0';                          // Clear command buff
    strcat(command, pip_path);                  // Append the path to pip exe   
    strcat(command, requirements_txt_path);     // Append the requirements.txt path (-r ..\backend\refs\requirements.txt)
    strcat(command, pip_output_str);            // Append redirect pipe (> ... 2>&1)

    // Build full command
    char full_command[600];
    snprintf(full_command, sizeof(full_command), "cmd.exe /C %s", command);

    // Execute pip command (with progress spinner)
    int pip_result = spinner_progress_printer(full_command);

    // Handle result
    if (pip_result == 0) {

        // FAILURE
        printf(BOLD_RED "ERROR: " RESET "Failed to install Python dependencies.\n");
        return 0; 
    }

    // SUCCESS
    printf(BOLD_GREEN "[+] SUCCESS: " RESET "Python environment and dependencies installed successfully.\n");

    // --- Install Frontend --- //
    printf(BOLD_WHITE "\n[+] Installing frontend (React) dependencies...\n" RESET);

    // Clear the buffer
    command[0] = '\0';

    // Build the command:
    strcat(command, "cmd.exe /C cd ");          // Change dir
    strcat(command, frontend_dir);              // Frontend directory path
    strcat(command, " && npm install ");        // npm install command
    strcat(command, npm_install_output_str);    // Redirect output 

    // Run the command
    int npm_install_result = spinner_progress_printer(command);

    // Check result
    if (npm_install_result == 0) {
        printf(BOLD_RED "ERROR: " RESET "Failed to install frontend dependencies.\n");
        return 0;
    }

    // SUCCESS
    printf(BOLD_GREEN "[+] SUCCESS: " RESET "Node modules installed successfully.\n");

    // --- Build frontend app --- //
    printf(BOLD_WHITE "[+] Building frontend application...\n" RESET);

    // Build the command:
    command[0] = '\0';                      // Clear buffer
    strcat(command, "cmd.exe /C cd ");      // Change dir
    strcat(command, frontend_dir);          // Frontend directory
    strcat(command, " && npm run build ");  // npm build command
    strcat(command, npm_build_output_str);  // Redirect output

    // Run command
    int npm_build_result = spinner_progress_printer(command);

    // Check result
    if (npm_build_result == 0) {
        printf(BOLD_RED "ERROR: " RESET "Failed to build frontend application.\n");
        return 0;
    }

    // Success
    printf(BOLD_GREEN "[+] SUCCESS: " RESET "Frontend built successfully.\n");


    // Install done
    return 1;
}