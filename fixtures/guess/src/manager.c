#include <stdio.h>
#include <stdlib.h>

int think;
int queries = 0;

int ask(int x) {
    queries++;
    if (queries > 20) {
        printf("too many queries\n");
        exit(0);
    }
    return x - think;
}

int guessNumber();

int main() {
    scanf("%d", &think);

    int ans = guessNumber();

    if (ans == think) {
        printf("ok\n");
    } else {
        printf("wrong answer\n");
    }
}