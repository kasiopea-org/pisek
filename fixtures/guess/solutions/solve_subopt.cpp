#include "stub.h"

int guessNumber() {
    for (int i=1; i<10; i++) {
        if (ask(i) != 0) {
            return i;
        }
        if (ask(i) != 0) {
            return i;
        }
    }
    return -1;
}
