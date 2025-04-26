#include <stdio.h>
#include "installer.h"

int main(int argc, char *argv[]) {
    printf("Starting installation...\n");

    // Call your installer logic
    if (perform_installation()) {
        printf("Installation completed successfully.\n");
    } else {
        printf("Installation failed.\n");
    }

    return 0;
}
