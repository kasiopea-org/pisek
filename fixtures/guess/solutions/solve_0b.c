#include "stub.h"

int guessNumber() {
    for (int i = 0; i <= 100; i++) {
        if (ask(i) == 0) {
            return i;
        }
    }

    return -1;
}
