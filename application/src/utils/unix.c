#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <fcntl.h>


extern volatile sig_atomic_t running;

void handle_sigint(int sig) {
    (void)sig;
    running = 0;
}

void setup_console_handler(void) {
    struct sigaction sa;
    sa.sa_handler = handle_sigint;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);
}

/** run_background_command_with_log()
 * @brief Spawns a child process to run the given command, redirecting stdout and stderr to the given log file.
 * @param command - the command to run
 * @param log_file - the file to redirect outputs to
 * @returns - pid_t, the PID of the child process.
 */
pid_t run_background_command_with_log(const char *command, const char *log_file) {
    pid_t pid = fork();

    if (pid == -1) {
        perror("fork");
        return -1;
    }

    if (pid == 0) {
        // In child
        int fd = open(log_file, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd == -1) {
            perror("open log file");
            exit(1);
        }

        dup2(fd, STDOUT_FILENO);
        dup2(fd, STDERR_FILENO);
        close(fd);

        execl("/bin/sh", "sh", "-c", command, (char *)NULL);
        perror("execl"); // Only reached if exec fails
        exit(1);
    }

    // Return parent process
    return pid;
}
