#include <assert.h>
#include <iostream>
#include <stdio.h>
#include <stdlib.h>

using namespace std;

void verdict(bool correct, string msg) {
    cout << msg << endl;
    exit(correct ? 42 : 43);
}

int main(int argc, char **argv) {
    FILE *fin = fopen(getenv("TEST_INPUT"), "r");
    FILE *fcorrect = fopen(getenv("TEST_OUTPUT"), "r");

    assert(fin && fcorrect);

    int t;
    fscanf(fin, "%d", &t);

    for (int i = 0; i < t; i++) {
        long long a, b, c, contestant;

        fscanf(fin, "%lld%lld", &a, &b);
        fscanf(fcorrect, "%lld", &c);

        scanf("%lld", &contestant);

        assert(a + b == c);

        if (c != contestant) {
            verdict(false, "No, that wasn't the correct answer.");
        }
    }

    verdict(true, "Yes, that was the correct answer");
}
