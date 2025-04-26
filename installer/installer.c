#include "installer.h"
#include <stdio.h>

#include "windows_tasks.h"
#include "unix_tasks.h"


int perform_installation() {
    printf("Dispatching to platform-specific install...\n");

#ifdef _WIN32
    return windows_install();
#else
    return unix_install();
#endif
}
