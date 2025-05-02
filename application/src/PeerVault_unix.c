#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/wait.h>

#include "misc.h"
#include "colors.h"
#include "unix_utils.h"

// Forward declare to avoid implicit-function warning 
int kill(pid_t pid, int sig);

// Global/extern vars
volatile sig_atomic_t running = 1;


int main(int argc, char *argv[]) {

    // NOTE: not using arc or argv
    (void)argc;
    (void)argv;

    // Print banner
    print_banner();
    printf("\n");

    // Construct command to activate the venv and start flask app
    char run_flask_cmd[512];
    snprintf(run_flask_cmd, sizeof(run_flask_cmd),
        "cd %s && source %s && %s",
        BACKEND_DIR,
        VENV_CMD,
        RUN_FLASK_CMD
    );

    // Construct command to start the frontend
    char run_react_cmd[256];
    snprintf(run_react_cmd, sizeof(run_react_cmd),
        "cd %s && %s",
        FRONTEND_DIR,
        RUN_REACT_CMD
    );

    // Start backend, create DB if needed
    int db_path_exists = path_exists(DB_PATH);
    if (db_path_exists) {
        printf(BOLD_GREEN "SUCCESS: " RESET "Database already exists at \"%s\"\n", DB_PATH);
    } else {
        printf(BOLD_YELLOW "NOTICE: " RESET "Creating database at \"%s\"\n", DB_PATH);

        char db_cmd[256];
        snprintf(db_cmd, sizeof(db_cmd), "cd %s && python3 %s", SETUP_BACKEND_DIR, CREATE_DB_PY);

        int create_result = system(db_cmd);
        if (create_result == 0) {
            printf(BOLD_GREEN "SUCCESS: " RESET "Database created successfully.\n");
        } else {
            printf(BOLD_RED "ERROR: " RESET "There was an error creating the database.\n");
        }
    }

    // Start Flask backend
    pid_t flask_pid = run_background_command_with_log(run_flask_cmd, FLASK_TERMINAL_LOG);
    if (flask_pid > 0) {
        printf(BOLD_GREEN "SUCCESS: " RESET "Flask backend started (PID: %d)\n", flask_pid);
    } else {
        printf(BOLD_RED "ERROR: " RESET "Failed to start Flask backend\n");
        return 1;
    }

    // Start React frontend
    pid_t react_pid = run_background_command_with_log(run_react_cmd, REACT_TERMINAL_LOG);
    if (react_pid > 0) {
        printf(BOLD_GREEN "SUCCESS: " RESET "React frontend started (PID: %d)\n", react_pid);
    } else {
        printf(BOLD_RED "ERROR: " RESET "Failed to start frontend\n");
        return 1;
    }

    // Setup signal handler and wait
    setup_console_handler();

    printf("\n-------------------------------------------------------\n");
    printf(BOLD_GREEN "\nPeerVault is running.\n" RESET "Press Ctrl+C or close the terminal to exit...\n\n");

    while (running) {
        sleep(1);
    }

    // Clean up on exit
    printf("Shutting down PeerVault...\n");
    kill(flask_pid, SIGTERM);
    kill(react_pid, SIGTERM);
    waitpid(flask_pid, NULL, 0);
    waitpid(react_pid, NULL, 0);
    printf("PeerVault exited.\n");

    return 0;
}
