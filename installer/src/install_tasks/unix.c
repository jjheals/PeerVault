#include <stdio.h>
#include <stdlib.h>
#include <string.h>           // For strcat()
#include <unistd.h>           // For sleep(), fork(), execvp()
#include <sys/wait.h>         // For waitpid()
#include "unix_tasks.h"
#include "colors.h"

/** spinner_progress_printer(command)
 * @brief Executes the given command and prints a spinner while executing. 
 * @param command the command to execute.
 * @return An integer, 1 if the command succeeds and 0 if it fails. 
 */
int spinner_progress_printer(char* command) {

    // Fork a new process
    pid_t pid = fork();
    if (pid < 0) {
        // Fork failed
        return 0;
    }
    else if (pid == 0) {
        // Child process
        execl("/bin/sh", "sh", "-c", command, (char *) NULL);
        // If execl fails
        perror("execl failed");
        exit(EXIT_FAILURE);
    }
    else {
        // Parent process
        const char spinner[] = "|/-\\";
        int spinner_index = 0;
        int status;

        // Spinner while waiting
        while (1) {
            pid_t result = waitpid(pid, &status, WNOHANG);
            if (result == 0) {
                // Child still running
                printf("\b%c", spinner[spinner_index]);
                fflush(stdout);
                spinner_index = (spinner_index + 1) % 4;
                sleep(1); // Sleep 100ms
            }
            else {
                // Child finished
                printf("\b \b"); // Clean spinner
                fflush(stdout);
                printf("\n");    // Newline
                break;
            }
        }

        // Check if child exited normally
        if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
            return 1; // Success
        }
        else {
            return 0; // Failure
        }
    }
}


/** unix_install()
 * @brief Handles the installation logic for Unix/Linux systems.
 * @return An integer, 1 if the install succeeds and 0 if it fails.
 */
int unix_install() {
    printf(BOLD_YELLOW "\n[Unix] Installing files...\n" RESET);

    // Define relative paths 
    char* venv_path = "../backend/venv";
    char* activate_venv_path = "../backend/venv/bin/activate";
    char* requirements_txt_path = "../backend/refs/requirements.txt";
    char* pip_path = "../backend/venv/bin/pip";
    char* pip_output_str = "> pip_output.log 2>&1";

    // Define buffer for building command strings
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
    printf(BOLD_WHITE "[+] Activated venv.\n" RESET);

    // Info print
    printf(BOLD_WHITE "[+] Installing Python dependencies via pip...\n" RESET);

    // Create the pip install command
    command[0] = '\0';                           // Clear command buff
    strcat(command, pip_path);                   // Append path to pip exe
    strcat(command, " install -r ");              // Install command
    strcat(command, requirements_txt_path);      // Requirements.txt path
    strcat(command, " ");                        // Space before output redirection
    strcat(command, pip_output_str);             // Redirect pip output

    // Execute pip command (with progress spinner)
    int pip_result = spinner_progress_printer(command);

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