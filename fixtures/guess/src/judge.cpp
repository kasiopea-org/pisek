#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <unistd.h>
using namespace std;

const int OPT_QUERIES = 10;
const int MAX_QUERIES = 20;

void verdict(double points, string msg){
    cerr << msg << endl;
	if (points == 0.0) {
        exit(43);
    } else {
        cerr << "POINTS=" << points << endl;
        exit(42);
    }
}

int main(int argc, char** argv) {
	FILE* fin = fopen(getenv("TEST_INPUT"), "r");
	assert(fin);

    char c;
    int x, q;
    fscanf(fin, "%d", &x);
    int queries = 0;
    while (true) {
        scanf(" %c %d", &c, &q);
        if (c == '?') {
            if (queries == MAX_QUERIES) {
                printf("-1\n");
                fflush(stdout);
                verdict(0, "Queries limit exceeded");
            }
            printf("%d\n", (x == q));
            fflush(stdout);
        } else if (c == '!') {
            if (x == q) {
                verdict(min(1.0, double(OPT_QUERIES) / double(queries)), "OK");
            } else {
                verdict(0, "Wrong");
            }
        } else {
            verdict(0, "Protocol violation.");
        }
        queries++;
    }
}
