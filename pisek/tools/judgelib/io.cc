/*
 *	I/O functions for judges
 *
 *	(c) 2021 Martin Mares <mj@ucw.cz>
 *
 *	Based on judge library from the Moe contest system by the same author.
 *	Can be freely distributed and used under the terms of the GNU GPL v2 or later.
 *
 *	SPDX-License-Identifier: GPL-2.0-or-later
 */

#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <fcntl.h>

using namespace std;

#include "judge.h"

#define BUFSIZE 65536

stream::stream()
{
	name = NULL;
	fd = -1;
	buf = pos = stop = end = NULL;
}

void stream::open_fd(const char *name, int fd, bool want_close)
{
	const char *slash = strrchr(name, '/');
	const char *basename = (slash ? slash+1 : name);
	this->fd = fd;
	this->want_close = want_close;
	buf = (u8 *) xmalloc(BUFSIZE);
	pos = stop = buf;
	end = buf + BUFSIZE;
	this->name = xstrdup(basename);
}

void stream::open_read(const char *name)
{
	int fd = open(name, O_RDONLY);
	if (fd < 0)
		die("Unable to open %s for reading: %m", name);
	open_fd(name, fd);
}

void stream::open_write(const char *name)
{
	int fd = open(name, O_WRONLY | O_CREAT | O_TRUNC, 0666);
	if (fd < 0)
		die("Unable to open %s for writing: %m", name);
	open_fd(name, fd);
}

void stream::flush()
{
	if (stop == buf && pos > buf) {
		u8 *p = buf;
		int len = pos - buf;
		while (len > 0) {
			int cnt = write(fd, p, len);
			if (cnt <= 0)
				die("Error writing %s: %m", name);
			p += cnt;
			len -= cnt;
		}
	}
	pos = buf;
}

stream::~stream()
{
	flush();
	if (want_close)
		close(fd);
	if (name)
		free(name);
	if (buf)
		free(buf);
}

int stream::refill()
{
	int len = read(fd, buf, BUFSIZE);
	if (len < 0)
		die("Error reading %s: %m", name);
	pos = buf;
	stop = buf + len;
	return len;
}

int stream::getc_slow()
{
	return (refill() ? *pos++ : -1);
}

int stream::peekc_slow()
{
	return (refill() ? *pos : -1);
}
