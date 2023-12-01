#include <stdio.h>
#include <stdlib.h>

int think;
int queries = 0;

int ask(int x) {
    printf("? %d\n", x);
    fflush(stdout);
    scanf(" %d", &x);
    return x;
}

int guessNumber();

int main() {
    int ans = guessNumber();
    printf("! %d\n", ans);
    fflush(stdout);
}
