/*
 *	Tokenizer for judges
 *
 *	(c) 2021 Martin Mares <mj@ucw.cz>
 *
 *	Based on judge library from the Moe contest system by the same author.
 *	Can be freely distributed and used under the terms of the GNU GPL v2 or later.
 *
 *	SPDX-License-Identifier: GPL-2.0-or-later
 */

#include <cstdio>
#include <cstdlib>
#include <cstdarg>
#include <cstring>
#include <cctype>
#include <limits.h>
#include <errno.h>

using namespace std;

#include "judge.h"

#define DEFAULT_MAX_TOKEN (32 << 20)

void tokenizer::init()
{
	maxsize = DEFAULT_MAX_TOKEN;
	report_lines = false;
	bufsize = 1;

	token = (char *) xmalloc(bufsize);
	toksize = 0;
	line = 1;
}

tokenizer::tokenizer(stream *source)
{
	src = source;
	close_src = false;
	init();
}

tokenizer::tokenizer(const char *source_file)
{
	src = new stream;
	src->open_read(source_file);
	close_src = true;
	init();
}

tokenizer::tokenizer(const char *source_name, int source_fd, bool want_close)
{
	src = new stream;
	src->open_fd(source_name, source_fd, want_close);
	close_src = true;
	init();
}

tokenizer::~tokenizer()
{
	free(token);
	if (close_src)
		delete src;
}

void tokenizer::reject(const char *msg, ...)
{
	va_list args;
	va_start(args, msg);
	fprintf(stderr, "Error at %s line %d: ", src->name, line);
	vfprintf(stderr, msg, args);
	fputc('\n', stderr);
	va_end(args);
	exit(43);
}

static bool is_white(int c)
{
  return (c == ' ' || c == '\t' || c == '\r' || c == '\n');
}

char *tokenizer::get_token()
{
	int c;

	// Skip whitespace
	do {
		c = src->getc();
		if (c < 0)
			return NULL;
		if (c == '\n') {
			line++;
			if (report_lines) {
				toksize = 0;
				token[0] = 0;
				return token;
			}
		}
	} while (is_white(c));

	// This is the token itself
	toksize = 0;
	do {
		token[toksize++] = c;
		if (toksize >= bufsize) {
			if (toksize > maxsize)
				reject("Token too long");
			bufsize *= 2;
			if (bufsize > maxsize)
				bufsize = maxsize + 1;
			token = (char *) xrealloc(token, bufsize);
		}
		c = src->getc();
	} while (c >= 0 && !is_white(c));

	if (c >= 0)
		src->ungetc();

	token[toksize] = 0;
	return token;
}

/*
 *  Parsing functions.
 */

#define PARSE(f, ...)						\
	char *end;						\
	errno = 0;						\
	if (!toksize)						\
		return false;					\
	if (isspace(*(unsigned char *)token))			\
		return false;					\
	*x = f(token, &end, ##__VA_ARGS__);			\
	return !(errno || end != token + toksize)

bool tokenizer::to_long(long int *x)
{
	PARSE(strtol, 10);
}

bool tokenizer::to_ulong(unsigned long int *x)
{
	if (token[0] == '-')		// strtoul accepts negative numbers, but we don't
		return false;
	PARSE(strtoul, 10);
}

bool tokenizer::to_longlong(long long int *x)
{
	PARSE(strtoll, 10);
}

bool tokenizer::to_ulonglong(unsigned long long int *x)
{
	if (token[0] == '-')		// strtoull accepts negative numbers, but we don't
		return false;
	PARSE(strtoull, 10);
}

bool tokenizer::to_double(double *x)
{
	PARSE(strtod);
}

bool tokenizer::to_long_double(long double *x)
{
	PARSE(strtold);
}

bool tokenizer::to_int(int *x)
{
	long int y;
	if (!to_long(&y) || y > INT_MAX || y < INT_MIN)
		return false;
	*x = y;
	return true;
}

bool tokenizer::to_uint(unsigned int *x)
{
	unsigned long int y;
	if (!to_ulong(&y) || y > UINT_MAX)
		return false;
	*x = y;
	return true;
}

#define GET(fn, type)									\
	type tokenizer::get_##fn()							\
	{										\
		type x;									\
		if (!get_token())							\
			reject("Unexpected end of file");				\
		if (!to_##fn(&x))							\
			reject("Expected " #fn);					\
		return x;								\
	}

GET(int, int)
GET(uint, unsigned int)
GET(long, long int)
GET(ulong, unsigned long int)
GET(double, double)
GET(long_double, long double)

void tokenizer::get_nl()
{
	char *tok = get_token();
	if (tok && *tok)
		reject("Expected end of line");
}
