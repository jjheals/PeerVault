#ifndef UNIX_UTILS_H
#define UNIX_UTILS_H

#include <sys/types.h>

// Define paths 
const char* BACKEND_DIR = "../backend/";
const char* SETUP_BACKEND_DIR = "../backend/setup-scripts/";
const char* DB_PATH = "../backend/data/database.db";
const char* FRONTEND_DIR = "../frontend/";


const char* FLASK_TERMINAL_LOG = "logs/flask_terminal.log";
const char* REACT_TERMINAL_LOG = "logs/react_terminal.log";

// Define cmd line commands for activating the app
const char* VENV_CMD = "venv/bin/activate";     // Command to activate the python venv
const char* RUN_FLASK_CMD = "python main.py";   // Command to run the flask app
const char* CREATE_DB_PY = "create_db.py";      // Python script that creates the database
const char* RUN_REACT_CMD = "npm run dev";      // CLI command to start the react app

// Funcs
void setup_console_handler(void);
pid_t run_background_command_with_log(const char *command, const char *log_file);

#endif
