#include <signal.h>

extern "C" int no_wait_children() {
    struct sigaction action = {};
    action.sa_handler = SIG_DFL;
    action.sa_flags = SA_NOCLDWAIT;
    if (sigemptyset(&action.sa_mask) != 0) return -1;
    return sigaction(SIGCHLD, &action, nullptr);
}
