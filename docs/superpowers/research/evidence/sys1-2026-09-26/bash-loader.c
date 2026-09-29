#include <stdlib.h>
#include <unistd.h>
int main(int argc, char **argv) {
    char **next = calloc((size_t)argc + 5, sizeof(char *));
    if (!next) return 126;
    next[0] = "/usr/lib/ld-linux-x86-64.so.2";
    next[1] = "--inhibit-cache";
    next[2] = "--library-path";
    next[3] = "/usr/lib";
    next[4] = "/usr/bin/bash";
    for (int i = 1; i < argc; ++i) next[i + 4] = argv[i];
    execv(next[0], next);
    return 127;
}
