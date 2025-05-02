#ifndef WINDOWS_H
#define WINDOWS_H

#include <windows.h>
#include <stdbool.h>

// Define paths 
const char* BACKEND_DIR = "..\\backend\\";
const char* SETUP_BACKEND_DIR = "..\\backend\\setup-scripts\\";
const char* DB_PATH = "../backend/data/database.db";
const char* FRONTEND_DIR = "../frontend/";


const char* FLASK_TERMINAL_LOG = "logs/flask_terminal.log";
const char* REACT_TERMINAL_LOG = "logs/react_terminal.log";

// Define cmd line commands for activating the app
const char* VENV_CMD = "venv\\Scripts\\activate.bat";   // Command to activate the python venv
const char* RUN_FLASK_CMD = "python main.py";           // Command to run the flask app
const char* CREATE_DB_PY = "create_db.py";              // Python script that creates the database
const char* RUN_REACT_CMD = "npm run dev";              // CLI command to start the react app

// Funcs 
int run_background_command_with_log(const char *command, const char *log_file, PROCESS_INFORMATION *out_pi);
BOOL WINAPI console_handler(DWORD signal);
void setup_console_handler(void);


#endif


