#include <guess.h>

#include <stdio.h>
#include <stdlib.h>

int ask(int x) {
    printf("? %d\n", x);
    fflush(stdout);
    scanf(" %d", &x);
    return x;
}

int main() {
    int ans = guessNumber();
    printf("! %d\n", ans);
    fflush(stdout);
}
