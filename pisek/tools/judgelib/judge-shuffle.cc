/*
 *	A judge comparing shuffled sequences of tokens
 *
 *	(c) 2021 Martin Mares <mj@ucw.cz>
 *
 *	Based on code from the Moe contest system, which is:
 *
 *	(c) 2007 Martin Mares <mj@ucw.cz>
 *
 *	Can be freely distributed and used under the terms of the GNU GPL v2 or later.
 *
 *	SPDX-License-Identifier: GPL-2.0-or-later
 */

#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <getopt.h>
#include <math.h>
#include <vector>
#include <algorithm>

using namespace std;

#include "judge.h"

static bool ignore_nl, ignore_empty, ignore_case;
static bool shuffle_lines, shuffle_words;

/*** Token buffer ***/

#define TOKBUF_PAGE 65536

struct tokpage {
	struct tokpage *next;
	char *pos, *end;
	char *buf;

	tokpage(uint size) {
		next = NULL;
		buf = (char *) xmalloc(size);
		pos = buf;
		end = buf + size;
	}
};

struct tokbuf {
	// For writing:
	tokpage *first_page, *last_page;
	uint num_tokens, num_lines;

	// For reading:
	tokpage *this_page;
	char *read_pos;

	tokbuf() {
		first_page = last_page = this_page = NULL;
		num_tokens = num_lines = 0;
		read_pos = NULL;
	}

	void add_token(const char *token, int l);
	void close();

	const char *get_first();
	const char *get_next();
};

void tokbuf::add_token(const char *token, int l)
{
	l++;
	tokpage *pg = last_page;
	if (!pg || pg->end - pg->pos < l) {
		if (pg)
			pg->end = pg->pos;
		int size = TOKBUF_PAGE;
		if (l > size/5)
			size = l;
		pg = new tokpage(size);
		if (last_page)
			last_page->next = pg;
		else
			first_page = pg;
		last_page = pg;
	}
	memcpy(pg->pos, token, l);
	pg->pos += l;
	num_tokens++;
	if (l == 1)
		num_lines++;
}

void tokbuf::close()
{
	if (last_page)
		last_page->end = last_page->pos;
}

const char *tokbuf::get_first()
{
	tokpage *pg = first_page;
	if (!pg)
		return NULL;
	this_page = pg;
	read_pos = pg->buf;
	return pg->buf;
}

const char *tokbuf::get_next()
{
	tokpage *pg = this_page;
	read_pos += strlen(read_pos) + 1;
	if (read_pos >= pg->end) {
		this_page = pg = pg->next;
		if (!pg)
			return NULL;
		read_pos = pg->buf;
	}
	return read_pos;
}

/*** Reading and shuffling ***/

struct tok {
	const char *token;
	uint hash;

	void compute_hash()
	{
		const char *x = token;
		hash = 1;
		while (*x)
			hash = (hash * 0x6011) + *x++;
	}

	int compare(const tok with) const
	{
		if (hash < with.hash)
			return -1;
		if (hash > with.hash)
			return 1;
		return strcmp(token, with.token);
	}

	bool operator < (const tok &with) const
	{
		return compare(with) < 0;
	}

	bool operator != (const tok &with) const
	{
		return compare(with) != 0;
	}
};

struct line {
	tok *toks;
	uint len;
	uint hash;
	uint orig_line;

	void compute_hash()
	{
		hash = 1;
		for (uint i=0; i < len; i++)
			hash = (hash * 0x6011) + toks[i].hash;
	}

	int compare(const line &with) const
	{
		if (hash < with.hash)
			return -1;
		if (hash > with.hash)
			return 1;

		if (len < with.len)
			return -1;
		if (len > with.len)
			return 1;

		for (uint i=0; i < len; i++) {
			int c = toks[i].compare(with.toks[i]);
			if (c)
				return c;
		}
		return 0;
	}

	bool operator < (const line &with) const
	{
		return compare(with) < 0;
	}

	bool operator != (const line &with) const
	{
		return compare(with) != 0;
	}
};

struct shuffler {
	tokbuf *tb;
	vector<tok> toks;
	vector<line> lines;
	uint num_lines;

	void read(tokenizer *tizer);
	void slurp(tokenizer *tizer);
};

void shuffler::slurp(tokenizer *tizer)
{
	tb = new tokbuf;
	char *token;
	bool nl = true;

	while (token = tizer->get_token()) {
		if (token[0]) {
			nl = false;
			if (ignore_case)
				for (char *c=token; *c; c++)
					if (*c >= 'a' && *c <= 'z')
						*c = *c - 'a' + 'A';
		} else if (!ignore_nl) {
			if (nl && ignore_empty)
				continue;
			nl = true;
		}
		tb->add_token(token, tizer->toksize);
	}

	if (!nl)
		tb->add_token("", 0);
	tb->close();
}

void shuffler::read(tokenizer *tizer)
{
	slurp(tizer);
	toks.resize(tb->num_tokens);
	lines.resize(tb->num_lines + 1);

	tok *t = toks.data();
	line *l = lines.data();
	l->toks = t;
	num_lines = 0;
	for (const char *x = tb->get_first(); x; x = tb->get_next()) {
		if (*x) {
			t->token = x;
			t->compute_hash();
			t++;
		} else {
			l->len = t - l->toks;
			if (shuffle_words) {
				auto beg = toks.begin() + (l->toks - toks.data());
				sort(beg, beg + l->len);
			}
			l->compute_hash();
			l->orig_line = ++num_lines;
			l++;
			l->toks = t;
		}
	}
	assert(l->toks == t);
	assert(num_lines == tb->num_lines);

	if (shuffle_lines)
		sort(lines.begin(), lines.end());

#if 0
	for (uint i=0; i < num_lines; i++) {
		line *l = &lines[i];
		printf("%08x %5d: ", l->hash, l->orig_line);
		for (uint j=0; j < l->len; j++) {
			tok *t = &l->toks[j];
			printf("<%08x|%s>", t->hash, t->token);
		}
		printf("\n");
	}
#endif
}

static void compare(shuffler *s1, shuffler *s2)
{
	if (s1->num_lines != s2->num_lines)
		reject("Output has %d lines, expecting %d", s1->num_lines, s2->num_lines);

	for (uint i=0; i<s1->num_lines; i++) {
		const line &l1 = s1->lines[i], &l2 = s2->lines[i];
		if (l1 != l2)
			reject("Line %d does not match", l1.orig_line);
	}
}

/*** Main ***/

static void usage()
{
	fprintf(stderr, "Usage: judge-shuffle [<options>] <output> <correct>\n\
\n\
Options:\n\
-e\t\tIgnore empty lines\n\
-i\t\tIgnore case\n\
-l\t\tShuffle lines (i.e., ignore their order)\n\
-n\t\tIgnore newlines and match the whole input as a single line\n\
-w\t\tShuffle words in each line\n\
");
	exit(1);
}

int main(int argc, char **argv)
{
	int opt;

	while ((opt = getopt(argc, argv, "eilnw")) >= 0) {
		switch (opt) {
			case 'n':
				ignore_nl = true;
				break;
			case 'e':
				ignore_empty = true;
				break;
			case 'l':
				shuffle_lines = true;
				break;
			case 'w':
				shuffle_words = true;
				break;
			case 'i':
				ignore_case = true;
				break;
			default:
				usage();
		}
	}
	if (optind + 2 != argc)
		usage();

	tokenizer t1(argv[optind]);
	tokenizer t2(argv[optind+1]);
	if (!ignore_nl)
		t1.report_lines = t2.report_lines = true;

	shuffler s1, s2;
	s1.read(&t1);
	s2.read(&t2);

	compare(&s1, &s2);
	return 42;
}
