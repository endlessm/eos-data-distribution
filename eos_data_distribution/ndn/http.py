#!/usr/bin/python
# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2016 Endless Mobile, Inc.
# Author: Niv Sardi <xaiki@endlessm.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# A copy of the GNU Lesser General Public License is in the file COPYING.

import argparse
import logging
import bisect

import gi
gi.require_version('Soup', '2.4')

from gi.repository import Soup
from gi.repository import GObject

from .dbus import chunks
from .. import defaults, utils

logger = logging.getLogger(__name__)


def make_soup_session():
    session = Soup.Session()
    session.props.ssl_strict = False
    session.props.max_conns = 100
    session.props.max_conns_per_host = 100
    return session


def fetch_http_headers(session, url):
    # XXX: SOMA's subscriptions-frontend doesn't handle HEAD requests yet because S3
    # is a bit silly with signed requests. For now, request a bytes=0-0 range and
    # return the full response_headers.
    msg = Soup.Message.new("GET", url)
    msg.request_headers.append('Range', 'bytes=0-0')
    session.send(msg, None)
    return msg.response_headers


def get_content_size(headers):
    content_range = headers.get_one('Content-Range')
    if not content_range:
        return -1
    size = int(content_range.split('/')[1])
    return size


def get_last_modified(headers):
    # note that we can't use ETag as we need things to be ordered
    date = Soup.Date.new_from_string(headers.get_one('Last-Modified'))
    if not date:
        return None
    return date.to_string(Soup.DateFormat.ISO8601)


class Getter(object):

    def __init__(self, url, onData, session=None, chunk_size=defaults.CHUNK_SIZE):
        super(Getter, self).__init__()

        self.url = url
        self.onData = onData
        self.chunk_size = chunk_size

        self._queue = list()
        self._data = dict()
        self._in_flight = None

        self._session = session
        if self._session is None:
            self._session = make_soup_session()

        # XXX -- this is a bit ugly that we're making an HTTP request
        # in the constructor here...
        self._headers = fetch_http_headers(self._session, self.url)
        self._size = get_content_size(self._headers)
        if self._size == -1:
            raise ValueError("Could not determine Content-Size for %s" % url)
        logger.debug('getter init: %s', url)

    def soup_get(self, n, count=1, cancellable=None):
        msg = Soup.Message.new('GET', self.url)
        _bytes = 'bytes=%d-%d' % (n * self.chunk_size, (n + count) * self.chunk_size - 1)
        logger.debug('GET %s', _bytes)
        msg.request_headers.append('Range', _bytes)
        self._session.queue_message(
            msg, lambda session, msg: self._got_reply(msg, (n, count)))
        logger.debug('getter: soup_get: %d', n)

    def _got_reply(self, msg, args):
        n, count = args
        if msg.status_code not in (Soup.Status.OK, Soup.Status.PARTIAL_CONTENT):
            logger.info('got error in soup_get: %s', msg.status_code)
            return

        buf = msg.get_property('response-body-data').get_data()
        bufs = [buf[i*self.chunk_size:(i+1)*self.chunk_size]for i in xrange(count)]
        [self._got_buf(b, n + i) for i, b in enumerate(bufs)]

    def _got_buf(self, buf, index):
        data = self._data[index]
        data.setContent(buf)
        self.onData(data)
        self._consume_queue()

    def queue_request(self, data, n):
        self._data[n] = data
        if not self._in_flight:
            self._in_flight = 1
            return self.soup_get(n)

        bisect.insort(self._queue, n)

    def _consume_queue(self):
        if len(self._queue) == 0:
            self._in_flight = None
            return

        n = self._queue[0]
        if len(self._queue) == 1:
            self._in_flight = 1
            return self.soup_get(n)

        # we are now sure to have more than 1 element
        simil = [e for i, e in enumerate(self._queue) if e == n + i]
        size = len(simil)
        del self._queue[:size]
        self._in_flight = len(self._queue)
        self.soup_get(n, size)

class Producer(chunks.Producer):

    def __init__(self, name, url, session=None, *args, **kwargs):
        self._getter = Getter(url, session=session,
                              onData=lambda d: self.sendFinish(d))
        super(Producer, self).__init__(
            name, cost=defaults.RouteCost.HTTP, *args, **kwargs)

    def _get_final_segment(self):
        return self._getter._size // self.chunk_size

    def _send_chunk(self, data, n):
        logger.info('HTTP send_chunk: %s', n)
        self._getter.queue_request(data, n)

if __name__ == '__main__':
    import re
    from .tests import utils as testutils

    # to use this you should call the module like this from the toplevel:
    # PYTHONPATH=. python3 -m eos_data_distribution.ndn.http "https://com-endless--cloud-soma-prod--shared-shard.s3-us-west-2.amazonaws.com/a76c961c62d543840f11719ed31b9e6f40cc7715469236c14d9c622422eac5ab.shard" -o test.shard

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cost", default=10)
    parser.add_argument("-o", "--output")
    parser.add_argument("url")
    args = utils.parse_args(parser=parser)

    if args.name:
        name = args.name
    else:
        name = re.sub('https?://', '', args.url)

    producer = Producer(name=name, url=args.url)
    testutils.run_producer_test(producer, name, args)
