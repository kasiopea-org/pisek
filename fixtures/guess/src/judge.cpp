#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <unistd.h>
using namespace std;

const int MAX_QUERIES = 10;

void verdict(int points, string msg){
	cerr << msg << endl;
	exit(43 - points);
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
                verdict(1, "OK");
            } else {
                verdict(0, "Wrong");
            }
        } else {
            cout << c << endl;
            verdict(0, "Protocol violation.");
        }
        queries++;
    }
}
