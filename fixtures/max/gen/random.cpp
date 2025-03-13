#include <random>

std::mt19937_64 rng;

void seed_rng(int seed) {
    rng.seed(seed);
}

long long rand_range(long long from, long long to) {
    to = std::max(to, from);
    // Vrati nahodny long long v intervalu [from, to] (tj. vcetne `to`).
    std::uniform_int_distribution<long long> dist(from, to);
    return dist(rng);
}
