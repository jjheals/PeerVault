#include <stdio.h>
#include "installer.h"
#include "colors.h"


int main(int argc, char *argv[]) {
    printf("Starting installation...\n");

    // Execute install function
    if (perform_installation()) {
        printf(BOLD_GREEN "[+] SUCCESS: " RESET "Installation completed successfully.\n");
    } else {
        printf("Installation failed.\n");
    }

    return 0;
}
