/* 
 * THIS PROGRAM IS NOT AT HOME HERE!
 * Report any changes to it's author.
 */


/*
 *	Text normalizer for KSP Open-data Submitter
 *
 *	(c) 2021 Martin Mareš <mj@ucw.cz>
 */

/*
 *  The input is read from stdin, normalized output written to stdout,
 *  an one-line error message to stderr.
 *
 *  Exit codes follow the convention for judge programs:
 *  42 for OK, 43 for wrong input, other codes for internal errors.
 */

#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef unsigned char byte;

void bug(char *msg)
{
	fprintf(stderr, "Internal error: %s\n", msg);
	exit(1);
}

void __attribute__((format(printf, 1, 2)))
error(char *msg, ...)
{
	va_list args;
	va_start(args, msg);
	vfprintf(stderr, msg, args);
	fputc('\n', stderr);
	va_end(args);
	exit(43);
}

/*
 *  An internal I/O buffering mechanism. It is faster than stdio,
 *  but more importantly, it guarantees the following properties:
 *
 *    -  If the read buffer is not completely full, the input
 *       stream has ended.
 *
 *    -  The write buffer always contains the most recent character
 *       written.
 */

byte rd_buf[4096];
int rd_pos, rd_len;
long long int rd_offset;	// file offset of the byte following buffered data

byte wr_buf[4096];
int wr_pos;

int rd_block(void)
{
	rd_pos = rd_len = 0;
	while (rd_len < sizeof(rd_buf)) {
		int n = read(0, rd_buf + rd_len, sizeof(rd_buf) - rd_len);
		if (n < 0)
			bug("Error while reading");
		if (!n)
			break;
		rd_len += n;
	}
	rd_offset += rd_len;
	return rd_len;
}

long long int rd_tell(void)
{
	return rd_offset - rd_len + rd_pos;
}

void wr_block(void)
{
	int i = 0;
	while (i < wr_pos) {
		int n = write(1, wr_buf + i, wr_pos - i);
		if (n <= 0)
			bug("Error while writing");
		i += n;
	}
	wr_pos = 0;
}

int rd_byte(void)
{
	if (rd_pos >= rd_len) {
		if (!rd_block())
			return -1;
	}
	return rd_buf[rd_pos++];
}

void wr_byte(byte c)
{
	if (wr_pos >= sizeof(wr_buf))
		wr_block();
	wr_buf[wr_pos++] = c;
}

void codepoint(int c, long long int pos)
{
	if (c < 32) {
		if (c == '\r')
			return;
		else if (c == '\n' || c == '\t')
			wr_byte(c);
		else
			error("File contains non-printable character (code %d at position %lld)", c, pos);
	} else if (c >= 0x7f) {
		if (c == 0x7f)
			error("File contains non-printable character (code %d at position %lld)", c, pos);
		else
			error("File contains non-printable character (code %d at position %lld)", c, pos);
	} else {
		wr_byte(c);
	}
}

void ascii(void)
{
	for (;;) {
		long long int pos = rd_tell();
		int c = rd_byte();
		if (c < 0)
			break;
		codepoint(c, pos);
	}
}

void utf16(bool is_be)
{
	for (;;) {
		long long int pos = rd_tell();
		int c1 = rd_byte();
		if (c1 < 0)
			return;
		int c2 = rd_byte();
		if (c2 < 0)
			error("File in UTF-16 contains incomplete character (at position %lld)", pos);
		if (is_be)
			codepoint((c1 << 8) | c2, pos);
		else
			codepoint((c2 << 8) | c1, pos);
	}
}

int main(void)
{
	int n = rd_block();
	if (!n)
		return 42;

	byte *b = rd_buf;
	if (n >= 3 && b[0] == 0xef && b[1] == 0xbb && b[2] == 0xbf) {
		// UTF-8 BOM
		rd_pos += 3;
		ascii();
	} else if (n >= 2 && b[0] == 0xff && b[1] == 0xfe) {
		// UTF-16-LE BOM
		rd_pos += 2;
		utf16(false);
	} else if (n >= 2 && b[0] == 0xfe && b[1] == 0xff) {
		// UTF-16-BE BOM
		rd_pos += 2;
		utf16(true);
	} else {
		ascii();
	}

	if (wr_pos > 0 && wr_buf[wr_pos-1] != '\n')
		wr_byte('\n');

	wr_block();
	return 42;
}
