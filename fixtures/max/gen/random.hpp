#include <random>

extern std::mt19937_64 rng;

void seed_rng(int seed);
long long rand_range(long long from, long long to);
