#include <stdio.h>
#include <stdbool.h>

#ifdef _WIN32
    #include <io.h>     // For _access
    #define access _access
    #define F_OK 0      // Test for existence
#else
    #include <unistd.h> // For access
#endif


/** print_banner() 
 * @brief Prints the banner to the terminal. 
 */
void print_banner() {
    printf("\n-----------------------------------------------------------\n");
    printf("\t_____            __      __         _ _ \n");   
    printf("\t|  __ \\           \\ \\    / /        | | |  \n");
    printf("\t| |__) |__  ___ _ _\\ \\  / /_ _ _   _| | |_ \n");
    printf("\t|  ___/ _ \\/ _ \\ '__\\ \\/ / _` | | | | | __|\n");
    printf("\t| |  |  __/  __/ |   \\  / (_| | |_| | | |_ \n");
    printf("\t|_|   \\___|\\___|_|    \\/ \\__,_|\\__,_|_|\\__|\n");        
    printf("\n-----------------------------------------------------------\n");             
}


/** path_exists() 
 * @brief Checks if the path exists. 
 * @param path - the path to check
 * @returns - int, 1 if the path exists and 0 if it does not. 
 */
int path_exists(const char* path) {
    return access(path, F_OK) != -1;
}