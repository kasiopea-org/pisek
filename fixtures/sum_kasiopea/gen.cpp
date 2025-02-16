#include <iostream>
#include <string.h>
#include <string>
#include <random>
#include <cassert>
using ll = long long;
using namespace std;

std::mt19937_64 rng;

ll randRange(ll from, ll to) {
    std::uniform_int_distribution<ll> dist(from, to);
    return dist(rng);
}

int main(int argc, char* argv[]) {
    if (argc != 3) {
        return 1;
    }

    int diff = atoi(argv[1]) - 1;
    cerr << strlen(argv[2]) << endl;
    int seed = strtoull(argv[2], NULL, 16) & 0x7fffffff;
    rng.seed(seed);

    ll MAX_ABS = (diff == 1) ? 1e18 : 1e9;

    int T = 10;
    cout << T << endl;

    for (int ti = 0; ti < T; ti++) {
        ll a = randRange(-MAX_ABS, MAX_ABS);
        ll b = randRange(-MAX_ABS, MAX_ABS);
        cout << a << " " << b << endl;
    }

    return 0;
}
