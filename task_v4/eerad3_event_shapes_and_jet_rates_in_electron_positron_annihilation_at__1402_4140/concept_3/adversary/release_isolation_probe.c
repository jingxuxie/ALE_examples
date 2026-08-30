#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    char parent_memory[128];
    int descriptor = open("/tmp/release-cache", O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (descriptor < 0) return 2;
    close(descriptor);
    descriptor = open("/work/release-cache", O_WRONLY | O_CREAT, 0600);
    if (descriptor >= 0 || errno != EROFS) return 3;
    descriptor = open("/trusted_runner.py", O_WRONLY);
    if (descriptor >= 0 || errno != EROFS) return 4;
    snprintf(parent_memory, sizeof(parent_memory), "/proc/%ld/mem", (long)getppid());
    descriptor = open(parent_memory, O_RDONLY);
    if (descriptor >= 0) return 5;
    return 0;
}
