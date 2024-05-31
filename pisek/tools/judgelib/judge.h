/*
 *	A simple library for judges
 *
 *	(c) 2021-2022 Martin Mares <mj@ucw.cz>
 *
 *	Based on judge library from the Moe contest system by the same author.
 */

#ifndef JUDGE_H
#define JUDGE_H

#include <cassert>
#include <cstdint>
#include <sys/types.h>

/* Types */

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;

typedef int8_t s8;
typedef int16_t s16;
typedef int32_t s32;
typedef int64_t s64;

typedef unsigned int uint;

/* GCC extensions */

#ifdef __GNUC__
#define NONRET __attribute__((noreturn))
#else
#define NONRET
#endif

/* Return codes */

enum judge_exit_code {
	EXIT_ACCEPT = 42,
	EXIT_REJECT = 43,
	EXIT_JUDGE_FAILURE = 44,
};

/* util.cc: Utility functions */

void accept(const char *msg, ...) NONRET;	// Report correct output
void reject(const char *msg, ...) NONRET;	// Report wrong output
void die(const char *msg, ...) NONRET;		// Dies with a judge error
void *xmalloc(size_t size);
void *xrealloc(void *p, size_t size);
char *xstrdup(const char *str);

/* io.cc: Simple buffered I/O streams */

class stream {
public:
	char *name;

	void open_read(const char *name);
	void open_write(const char *name);
	void open_fd(const char *name, int fd, bool want_close=true);
	void flush();
	stream();
	~stream();

	int getc()
	{
		return (pos < stop) ? *pos++ : getc_slow();
	}

	int peekc()
	{
		return (pos < stop) ? *pos : peekc_slow();
	}

	void putc(int c)
	{
		if (pos >= end)
			flush();
		*pos++ = c;
	}

	void ungetc()
	{
		assert(pos > buf);
		pos--;
	}

private:
	int fd;
	bool want_close;
	u8 *buf;
	u8 *pos, *stop, *end;

	int refill();
	int getc_slow();
	int peekc_slow();
};

/* token.cc: Tokenization of input */

class tokenizer {
public:
	// Configurable parameters
	uint maxsize;		// Maximal allowed token size
	bool report_lines;	// Report an empty token at the end of each line

	// Current token after get_token() is called
	char *token;		// Current token (in the buffer)
	uint toksize;		// ... and its size
	uint line;		// ... and line number at its end

	tokenizer(stream *source);
	tokenizer(const char *source_file);
	tokenizer(const char *source_name, int source_fd, bool want_close=true);
	~tokenizer();
	void reject(const char *msg, ...) NONRET;
	char *get_token();	// Returns NULL at the end of input

	// Parsing functions
	bool to_int(int *x);
	bool to_uint(unsigned int *x);
	bool to_long(long int *x);
	bool to_ulong(unsigned long int *x);
	bool to_longlong(long long int *x);
	bool to_ulonglong(unsigned long long int *x);
	bool to_double(double *x);
	bool to_long_double(long double *x);

	// get_token() + parse or reject()
	int get_int();
	unsigned int get_uint();
	long int get_long();
	unsigned long int get_ulong();
	long long int get_longlong();
	unsigned long long int get_ulonglong();
	double get_double();
	long double get_long_double();
	void get_nl();

private:
	stream *src;
	bool close_src;
	uint bufsize;		// Allocated buffer size
	void init();
};

/* random.cc: Random generator */

class random_generator {
public:
	random_generator(u64 seed) { _init(seed); }
	random_generator(const char *hex_seed);
	u64 next_u64();
	u32 next_u32();
	uint next_range(uint size);
	uint next_range(uint start, uint past_end);

	// Our RNG can be used as a random engine in the C++ standard library
	using result_type = u32;
	u32 operator () () { return next_u32(); }
	static constexpr u32 min() { return 0; }
	static constexpr u32 max() { return ~(u32)0; }

private:
	u64 state[2];
	void _init(u64 seed);
};

#endif
