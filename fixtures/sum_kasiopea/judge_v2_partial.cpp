#include <array>
#include <assert.h>
#include <iostream>
#include <stdio.h>
#include <stdlib.h>

using namespace std;

void verdict(float points, string msg) {
    cout << msg << endl;
    cout << "POINTS=" << points << endl;
    exit(points > 0 ? 42 : 43);
}

std::array<double, 3> max_points = {1, 4, 6};

int main(int argc, char **argv) {
    assert(argc == 3);

    int subtask;
    assert(sscanf(argv[1], "%d", &subtask) == 1);

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
            verdict(0.0, "No, that wasn't the correct answer.");
        }
    }

    verdict(max_points.at(subtask), "Yes, that was the correct answer");
}
