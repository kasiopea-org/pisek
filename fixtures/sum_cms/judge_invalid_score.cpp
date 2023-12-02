#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <iostream>

using namespace std;

void verdict(float pts, string msg){
	cout << pts << endl;
	cerr << msg << endl;
	exit(0);
}

int main(int argc, char** argv) {
	assert(argc == 4);

	long long a, b, c, contestant;

	FILE* fin = fopen(argv[1], "r");
	FILE* fcorrect = fopen(argv[2], "r");
	FILE* fcontestant = fopen(argv[3], "r");

	assert(fin && fcorrect && fcontestant);

	fscanf(fin, "%lld%lld", &a, &b);
	fscanf(fcorrect, "%lld", &c);
	fscanf(fcontestant, "%lld", &contestant);

	assert(a + b == c);
	if (c == contestant) {
		// Bad score
		verdict(1.5, "OK");
	}

	if (contestant == abs(a) + abs(b))
		verdict(0.5, "|OK|");

	verdict(0.0, "WA");
}
