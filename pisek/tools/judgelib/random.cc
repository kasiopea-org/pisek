/*
 *	Random generator for judges
 *
 *	(c) 2022 Martin Mares <mj@ucw.cz>
 */

/*
 * This is the xoroshiro128+ random generator, designed in 2016 by David Blackman
 * and Sebastiano Vigna, distributed under the CC-0 license. For more details,
 * see http://vigna.di.unimi.it/xorshift/.
 *
 * Rewritten to C++ by Martin Mares, also placed under CC-0.
 */

#include <cstdlib>
#include <cstdio>

using namespace std;

#include "judge.h"

void random_generator::_init(u64 seed)
{
	state[0] = seed * 0xdeadbeef;
	state[1] = seed ^ 0xc0de1234;
	for (int i=0; i<100; i++)
	    next_u64();
}

random_generator::random_generator(const char *hex_seed)
{
	_init(strtoul(hex_seed, NULL, 16));
}

inline u64 rotl(u64 x, int k)
{
	return (x << k) | (x >> (64 - k));
}

u64 random_generator::next_u64()
{
	u64 s0 = state[0], s1 = state[1];
	u64 result = s0 + s1;
	s1 ^= s0;
	state[0] = rotl(s0, 55) ^ s1 ^ (s1 << 14);
	state[1] = rotl(s1, 36);
	return result;
}

u32 random_generator::next_u32()
{
	return next_u64() >> 11;
}

uint random_generator::next_range(uint size)
{
	// This is not perfectly uniform, but since size is 32-bit
	// and generator range 64-bit, the non-uniformity will be
	// negligible.
	return next_u64() % size;
}

uint random_generator::next_range(uint start, uint past_end)
{
	return start + next_range(past_end - start);
}
