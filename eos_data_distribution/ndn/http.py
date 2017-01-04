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

import logging

import gi
gi.require_version('Soup', '2.4')

from gi.repository import Soup
from gi.repository import GObject

from . import chunks

logger = logging.getLogger(__name__)
DEFAULT_COST = 10


def make_soup_session():
    session = Soup.Session()
    session.props.ssl_strict = False
    session.props.max_conns = 100
    session.props.max_conns_per_host = 100
    return session

def read_from_stream_async(istream, callback, cancellable=None, chunk_size=chunks.CHUNK_SIZE):
    chunks = []

    def got_data(istream, res):
        gbytes = istream.read_bytes_finish(res)
        chunks.append(gbytes.get_data())
        if gbytes.get_size() == 0:
            callback(''.join(chunks))
        else:
            read_bytes_async()

    def read_bytes_async():
        istream.read_bytes_async(chunk_size, 0, cancellable, got_data)

    read_bytes_async()

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
    size = int(content_range.split('/')[1])
    return size

def get_last_modified(headers):
    # note that we can't use ETag as we need things to be ordered
    date = Soup.Date.new_from_string(headers.get_one('Last-Modified'))
    return date.to_string(Soup.DateFormat.ISO8601)

class Getter(GObject.GObject):
    __gsignals__ = {
        'data': (GObject.SIGNAL_RUN_FIRST, None, (object, )),
    }

    def __init__(self, url, session=None, chunk_size=chunks.CHUNK_SIZE):
        super(Getter, self).__init__()

        self.url = url
        self.chunk_size = chunk_size

        self._session = session
        if self._session is None:
            self._session = make_soup_session()

        # XXX -- this is a bit ugly that we're making an HTTP request
        # in the constructor here...
        self._headers = fetch_http_headers(self._session, self.url)
        self._size = get_content_size(self._headers)
        self._last_modified = get_last_modified(self._headers)
        logger.debug('getter init: %s', url)

    def soup_get(self, data, n, cancellable=None):
        msg = Soup.Message.new('GET', self.url)
        msg.request_headers.append('Range', 'bytes=%d-%d' % (n * self.chunk_size, (n + 1) * self.chunk_size - 1))
        self._session.send_async(msg, cancellable, lambda session, task: self._got_stream(msg, task, data))
        logger.debug('getter: soup_get: %d', n)

    def _got_stream(self, msg, task, data):
        if msg.status_code not in (Soup.Status.OK, Soup.Status.PARTIAL_CONTENT):
            return

        istream = self._session.send_finish(task)
        read_from_stream_async(istream, lambda buf: self._got_buf(data, buf))

    def _got_buf(self, data, buf):
        data.setContent(buf)
        self.emit('data', data)
        logger.debug ('getter: got buf')

class Producer(chunks.Producer):
    def __init__(self, name, url, session=None, *args, **kwargs):
        super(Producer, self).__init__(name, cost=DEFAULT_COST, *args, **kwargs)
        self._getter = Getter(url, session=session, chunk_size=self.chunk_size)
        self._getter.connect('data', lambda o, d: self.sendFinish(d))

    def _get_final_segment(self):
        return self._getter._size // self.chunk_size

    def _send_chunk(self, data, n):
        self._getter.soup_get(data, n)

if __name__ == '__main__':
    import re
    from . import test

    parser = test.process_args()
    parser.add_argument("-c", "--cost", default=10)
    args = parser.parse_args()


    if args.name:
        name = args.name
    else:
        name = re.sub('https?://', '', args.url)

    producer = Producer(name=name, url=args.url)
    test.run_producer_test(producer, name, args)
