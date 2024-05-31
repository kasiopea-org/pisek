/*
 *	Utility functions for judges
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

using namespace std;

#include "judge.h"

void accept(const char *msg, ...)
{
	va_list args;
	va_start(args, msg);
	vfprintf(stderr, msg, args);
	fputc('\n', stderr);
	va_end(args);
	exit(EXIT_ACCEPT);
}

void reject(const char *msg, ...)
{
	va_list args;
	va_start(args, msg);
	vfprintf(stderr, msg, args);
	fputc('\n', stderr);
	va_end(args);
	exit(EXIT_REJECT);
}

void die(const char *msg, ...)
{
	va_list args;
	va_start(args, msg);
	vfprintf(stderr, msg, args);
	fputc('\n', stderr);
	va_end(args);
	exit(EXIT_JUDGE_FAILURE);
}

void *xmalloc(size_t size)
{
	void *p = malloc(size);
	if (!p)
		die("Out of memory (unable to allocate %z bytes)", size);
	return p;
}

void *xrealloc(void *p, size_t size)
{
	p = realloc(p, size);
	if (!p)
		die("Out of memory (unable to allocate %z bytes)", size);
	return p;
}

char *xstrdup(const char *str)
{
	size_t len = strlen(str) + 1;
	char *copy = (char *) xmalloc(len);
	memcpy(copy, str, len);
	return copy;
}
