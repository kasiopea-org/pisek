#include "stub.h"

int guessNumber() {
    int mn = 0, mx = 100;

    while (mn <= mx) {
        int mid = (mn + mx) / 2;
        int ans = ask(mid);

        if (ans == 0) {
            return mid;
        } else if (ans < 0) {
            mn = mid + 1;
        } else {
            mx = mid - 1;
        }
    }

    return mn;
}
