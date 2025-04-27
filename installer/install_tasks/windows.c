#include <stdio.h>
#include <stdlib.h>
#include <string.h>              // For strcat()
#include <windows.h>             // For CreateProcess(), ZeroMemory, etc.
#include <time.h>                // For sleep()
#include "windows_tasks.h"
#include "colors.h"


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

    // Define relative paths 
    char* venv_path = "..\\backend\\venv";
    char* activate_venv_path = "..\\backend\\venv\\Scripts\\activate";
    char* requirements_txt_path = "..\\backend\\refs\\requirements.txt";
    char* pip_path = "..\\backend\\venv\\Scripts\\pip";
    char* pip_output_str = "> pip_output.log 2>&1";

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
    printf(BOLD_GREEN "\n[+] SUCCESS: " RESET "Python environment and dependencies installed successfully.\n");
    return 1;
}