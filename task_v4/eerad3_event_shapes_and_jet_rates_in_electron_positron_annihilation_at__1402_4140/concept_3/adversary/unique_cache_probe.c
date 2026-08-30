#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>

static int check_storage(void) {
    if (access("/tmp/previous-native-process", F_OK) == 0) return 2;
    int temporary = open("/tmp/previous-native-process", O_CREAT | O_WRONLY, 0600);
    if (temporary < 0) return 3;
    close(temporary);
    int persistent = open("/work/persistent-cache", O_CREAT | O_WRONLY, 0600);
    if (persistent >= 0 || errno != EROFS) return 4;
    int supervisor = open("/trusted_runner.py", O_WRONLY);
    if (supervisor >= 0 || errno != EROFS) return 5;
    return 0;
}

void eerad3_batch(void *inputs, void *outputs, int count) {
    const unsigned char *input_bytes = inputs;
    const unsigned char *output_bytes = outputs;
    uint32_t input_count;
    if (memcmp(input_bytes, "ERAD3B4\0", 8) != 0) _exit(7);
    if (memcmp(output_bytes, "ERAD3O4\0", 8) != 0) _exit(8);
    memcpy(&input_count, input_bytes + 8, sizeof(input_count));
    if (count != 1 || input_count != 1 || memcmp(input_bytes + 12, "\0\0\0\0", 4) != 0) _exit(9);
    for (unsigned int offset = 16; offset < 688; offset++) {
        if (output_bytes[offset] != 0) _exit(10);
    }
    _exit(check_storage());
}
