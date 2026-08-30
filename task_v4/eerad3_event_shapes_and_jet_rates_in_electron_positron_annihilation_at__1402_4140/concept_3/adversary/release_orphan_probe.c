#define _POSIX_C_SOURCE 200809L
#include <time.h>
#include <unistd.h>

int main(void) {
    pid_t child = fork();
    if (child < 0) return 2;
    if (child == 0) {
        struct timespec started, current;
        double elapsed;
        clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &started);
        do {
            clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &current);
            elapsed = current.tv_sec - started.tv_sec;
            elapsed += (current.tv_nsec - started.tv_nsec) * 1e-9;
        } while (elapsed < 0.18);
        _exit(0);
    }
    return 0;
}
