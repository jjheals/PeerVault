#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "colors.h"

// Global/extern vars
HANDLE job_handle = NULL;   // Global job object for lifecycle management
extern BOOL running;        // Defined in main.c


/** run_background_command_with_log()
 * @brief Starts a shell in the background and executes the given command.
 * @param command - the command to execute
 * @param log_file - a file to redirect the processes' outputs
 * @param out_pi - a pointer to a process information obj to save the PID
 * @returns - 0 if fail, 1 if success 
 * 
 */
int run_background_command_with_log(const char *command, const char *log_file, PROCESS_INFORMATION *out_pi) {

    // Init vars
    STARTUPINFO si;
    PROCESS_INFORMATION pi;
    HANDLE hFile;

    // Create job object if not already
    if (job_handle == NULL) {
        job_handle = CreateJobObject(NULL, NULL);
        if (!job_handle) {
            printf("Failed to create Job Object: %lu\n", GetLastError());
            return 0;
        }

        JOBOBJECT_EXTENDED_LIMIT_INFORMATION jeli = { 0 };
        jeli.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;

        if (!SetInformationJobObject(job_handle, JobObjectExtendedLimitInformation, &jeli, sizeof(jeli))) {
            printf("Failed to configure Job Object: %lu\n", GetLastError());
            CloseHandle(job_handle);
            job_handle = NULL;
            return 0;
        }
    }

    // Open log file
    hFile = CreateFileA(
        log_file,
        GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        NULL,
        CREATE_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        NULL
    );

    // Make sure log file was opened correctly
    if (hFile == INVALID_HANDLE_VALUE) {
        printf("Failed to open log file '%s': %lu\n", log_file, GetLastError());
        return 0;
    }

    // Prepare STARTUPINFO
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags |= STARTF_USESTDHANDLES;
    si.hStdOutput = hFile;
    si.hStdError  = hFile;

    ZeroMemory(&pi, sizeof(pi));

    // Build full command string
    char cmdline[512];
    snprintf(cmdline, sizeof(cmdline), "cmd.exe /C \"%s\"", command);

    // Launch process
    BOOL success = CreateProcessA(
        NULL,               // Application name (use cmd.exe via command line)
        cmdline,            // Command line (MUST be mutable)
        NULL,               // Process security
        NULL,               // Thread security
        TRUE,               // Inherit handles for redirection
        CREATE_NO_WINDOW,   // NOTE: use CREATE_NO_WINDOW when stable (or 0 for debug)
        NULL,               // Env
        NULL,               // Working dir
        &si,
        &pi
    );

     // Close the log file after process is created
    CloseHandle(hFile); 

    // Check if successful
    if (!success) {
        DWORD err = GetLastError();
        printf(BOLD_RED "ERROR: " RESET "Failed to start process (WinErr %lu)\n", err);
        return 0;
    }

    // Assign process to the job so it's killed when the app exits
    if (!AssignProcessToJobObject(job_handle, pi.hProcess)) {
        printf(BOLD_RED "ERROR: " RESET "Failed to assign process to job object: %lu\n", GetLastError());
        TerminateProcess(pi.hProcess, 1);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        return 0;
    }

    // Return process info
    if (out_pi) {
        *out_pi = pi;
    } else {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }

    return 1;
}


/** console_handler()
 * @brief Handler to kill child processes when the program exits or is quit. 
 * @param signal - a dword obj for the shutdown signal
 * @returns - BOOL, TRUE when successful. 
 */
BOOL WINAPI console_handler(DWORD signal) {
    if (signal == CTRL_CLOSE_EVENT || signal == CTRL_C_EVENT) {
        printf(BOLD_YELLOW "NOTICE: " RESET "Shutting down PeerVault gracefully...\n\n");
        running = FALSE;
    }
    return TRUE;
}


/** setup_console_handler() 
 * @brief Wrapper for SetConsoleCtrlHandler that uses console_handler() as a callback. 
 */
void setup_console_handler(void) {
    SetConsoleCtrlHandler(console_handler, TRUE);
}