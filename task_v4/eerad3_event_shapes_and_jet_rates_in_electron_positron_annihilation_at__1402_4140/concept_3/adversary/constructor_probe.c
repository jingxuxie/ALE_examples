#define _POSIX_C_SOURCE 200809L
#include <time.h>
#include <unistd.h>

static pid_t constructor_process;

__attribute__((constructor)) static void initialize(void) {
    struct timespec started, current;
    double elapsed;
    constructor_process = getpid();
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &started);
    do {
        clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &current);
        elapsed = current.tv_sec - started.tv_sec;
        elapsed += (current.tv_nsec - started.tv_nsec) * 1e-9;
    } while (elapsed < 0.15);
}

void eerad3_batch(void *inputs, void *outputs, int count) {
    (void) inputs;
    (void) outputs;
    (void) count;
    if (constructor_process != getpid()) _exit(2);
}
