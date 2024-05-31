/*
 *	A judge comparing two sequences of tokens
 *
 *	(c) 2021 Martin Mares <mj@ucw.cz>
 *
 *	Based on code from the Moe contest system, which is:
 *
 *	(c) 2007 Martin Krulis <bobrik@matfyz.cz>
 *	(c) 2007 Martin Mares <mj@ucw.cz>
 *
 *	Can be freely distributed and used under the terms of the GNU GPL v2 or later.
 *
 *	SPDX-License-Identifier: GPL-2.0-or-later
 */

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <getopt.h>
#include <math.h>

using namespace std;

#include "judge.h"

static bool ignore_nl, ignore_trailing_nl, ignore_case;
static bool real_mode;
static double rel_eps = 1e-5;
static double abs_eps = 1e-30;

static bool tokens_equal(tokenizer *t1, tokenizer *t2)
{
	if (real_mode) {
		double x1, x2;
		if (t1->to_double(&x1) && t2->to_double(&x2)) {
			if (x1 == x2)
				return true;
			double eps = fabs(x2 * rel_eps);
			if (eps < abs_eps)
				eps = abs_eps;
			return (fabs(x1-x2) <= eps);
		}
		// If they fail to convert, compare them as strings.
	}
	return !(ignore_case ? strcasecmp : strcmp)(t1->token, t2->token);
}

static bool trailing_nl(tokenizer *t)
{
	// Ignore empty lines at the end of file
	if (t->token[0] || !ignore_trailing_nl)
		return false;
	t->report_lines = false;
	return !t->get_token();
}

static void usage(void)
{
	fprintf(stderr, "Usage: judge-token [<options>] <output> <correct>\n\
\n\
Options:\n\
-n\t\tIgnore newlines\n\
-t\t\tIgnore newlines at the end of file\n\
-i\t\tIgnore differences in letter case\n\
-r\t\tMatch tokens as real numbers and allow small differences:\n\
-e <epsilon>\tSet maximum allowed relative error (default: %g)\n\
-E <epsilon>\tSet maximum allowed absolute error (default: %g)\n\
", rel_eps, abs_eps);
	exit(1);
}

int main(int argc, char **argv)
{
	int opt;

	while ((opt = getopt(argc, argv, "ntire:E:")) >= 0) {
		switch (opt) {
			case 'n':
				ignore_nl = true;
				break;
			case 't':
				ignore_trailing_nl = true;
				break;
			case 'i':
				ignore_case = true;
				break;
			case 'r':
				real_mode = true;
				break;
			case 'e':
				rel_eps = atof(optarg);
				break;
			case 'E':
				abs_eps = atof(optarg);
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

	for (;;) {
		char *a = t1.get_token(), *b = t2.get_token();
		if (!a) {
			if (b && !trailing_nl(&t2))
				t1.reject("Ends too early");
			break;
		} else if (!b) {
			if (a && !trailing_nl(&t1))
				t2.reject("Garbage at the end");
			break;
		} else if (!tokens_equal(&t1, &t2)) {
			t1.reject("Found <%s>, expected <%s>", a, b);
		}
	}

	return 42;
}
