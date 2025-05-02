#include <stdio.h>
#include <string.h>
#include <windows.h>
#include <stdbool.h>

#include "misc.h"
#include "colors.h"

#include "windows_utils.h"


// Global/extern vars
BOOL running = TRUE;


int main(int argc, char *argv[]) {
    
    // NOTE: not using arc or argv
    (void)argc;
    (void)argv;

    // Init vars 
    STARTUPINFO si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    PROCESS_INFORMATION backend_proc;   // Pointer to the flask shell's process
    PROCESS_INFORMATION frontend_proc;  // Pointer to the react shell's process

    // Print the "PeerVault" banner to the terminal 
    print_banner();
    printf("\n");

    // Construct command to activate the venv and start flask app
    char run_flask_cmd_line[512];
    strcpy(run_flask_cmd_line, "cd ");
    strcat(run_flask_cmd_line, BACKEND_DIR);
    strcat(run_flask_cmd_line, " && call ");
    strcat(run_flask_cmd_line, VENV_CMD);
    strcat(run_flask_cmd_line, " && ");
    strcat(run_flask_cmd_line, RUN_FLASK_CMD);

    // Construct the command to start the frontend react app
    char run_react_cmd_line[256];
    strcpy(run_react_cmd_line, "cd ");
    strcat(run_react_cmd_line, FRONTEND_DIR);
    strcat(run_react_cmd_line, " && ");
    strcat(run_react_cmd_line, RUN_REACT_CMD);

    // Start backend, create DB if needed
    int db_path_exists = path_exists(DB_PATH);

    // Act according to db path exists result
    if(db_path_exists) {

        // Log that the DB exists
        printf(BOLD_GREEN "SUCCESS: " RESET "Database already exists at \"%s\"\n", DB_PATH);
    
    } else {
        // Log that we are creating the DB
        printf(BOLD_YELLOW "NOTICE: " RESET "Creating database at \"%s\"\n", DB_PATH);

        // Construct command to run the create_db.py script
        char db_cmd_line[256];
        strcpy(db_cmd_line, "cmd.exe /c \"cd ");
        strcat(db_cmd_line, SETUP_BACKEND_DIR);
        strcat(db_cmd_line, " && python ");
        strcat(db_cmd_line, CREATE_DB_PY);
        strcat(db_cmd_line, "\"");

        // Run using system() so it blocks until finished
        int create_db_result = system(db_cmd_line);

        // Handle result (0 means success)
        if (create_db_result == 0) {
            printf(BOLD_GREEN "SUCCESS: " RESET "Database created successfully.\n");
        } else {
            printf(BOLD_RED "ERROR: " RESET "There was an error creating the database.\n");
        }
    }

    // Run the flask app in the background, redirecting output to the FLASK_TERMINAL_LOG 
    if (run_background_command_with_log(run_flask_cmd_line, FLASK_TERMINAL_LOG, &backend_proc)) {
        printf(BOLD_GREEN "SUCCESS: " RESET "venv activated and flask backend started successfully (PID: %lu).\n", backend_proc.dwProcessId);        
        
        // Start the console handler
        setup_console_handler();
    }
    else {
        printf(BOLD_RED "ERROR: " RESET "failed to launch backend (WinErr %lu)\n", GetLastError());
        return 0;
    }

    // Start the frontend 
    if(run_background_command_with_log(run_react_cmd_line, REACT_TERMINAL_LOG, &frontend_proc)) {
        printf(BOLD_GREEN "SUCCESS: " RESET "frontend (React) app started successfully (PID: %lu).\n", frontend_proc.dwProcessId);        
    } else {
        printf(BOLD_RED "ERROR: " RESET "failed to launch frontend (React) app (WinErr %lu)\n", GetLastError());
        return 0;
    }

    // Run until the user exits 
    printf("\n-------------------------------------------------------\n");
    printf(BOLD_GREEN "\nPeerVault is running.\n" RESET "Press Ctrl+C or close the window to exit...\n\n");

    while (running) { Sleep(100); }

    // Print exit message and return
    printf("PeerVault exited.\n\n");
    return 0;
}