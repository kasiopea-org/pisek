#include <random>

std::mt19937_64 rng;

void seed_rng(int seed) {
    rng.seed(seed);
}

long long rand_range(long long from, long long to) {
    to = std::max(to, from);
    // Returns a random long long from the interval [from, to] (including "to").
    std::uniform_int_distribution<long long> dist(from, to);
    return dist(rng);
}
