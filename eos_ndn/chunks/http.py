#!/usr/bin/python
# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2016 Endless Computers INC.
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

from . import base

logger = logging.getLogger(__name__)


def make_soup_session():
    session = Soup.Session()
    session.props.ssl_strict = False
    session.props.max_conns = 100
    session.props.max_conns_per_host = 100
    return session

def read_from_stream_async(istream, callback, cancellable=None, chunk_size=base.CHUNK_SIZE):
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

def get_content_size(session, url):
    # XXX: SOMA's subscriptions-frontend doesn't handle HEAD requests yet because S3
    # is a bit silly with signed requests. For now, request a bytes=0-0 range and
    # look at the Content-Range.
    msg = Soup.Message.new("GET", url)
    msg.request_headers.append('Range', 'bytes=0-0')
    session.send(msg, None)
    content_range = msg.response_headers.get_one('Content-Range')
    size = int(content_range.split('/')[1])
    return size

class Producer(base.Producer):
    def __init__(self, name, url, session=None, *args, **kwargs):
        super(Producer, self).__init__(name, *args, **kwargs)

        self.url = url

        self._session = session
        if self._session is None:
            self._session = make_soup_session()

        # XXX -- this is a bit ugly that we're making an HTTP request
        # in the constructor here...
        self._size = get_content_size(self._session, self.url)

    def _get_final_block_id(self):
        return self._size / self.chunk_size

    def _send_chunk(self, n, data):
        self._soup_get(self.url, n, data)

    def _soup_get(self, uri, n, data, cancellable=None):
        msg = Soup.Message.new('GET', uri)
        req_range = (n * self.chunkSize, (n + 1) * self.chunkSize - 1)
        msg.request_headers.append('Range', 'bytes=%d-%d' % req_range)
        self.session.send_async(msg, cancellable, lambda session, task: self._got_stream(session, task, data_template))

    def _got_stream(self, session, task, data):
        if msg.status_code not in (Soup.Status.OK, Soup.Status.PARTIAL_CONTENT):
            return

        istream = session.send_finish(task)
        read_from_stream_async(istream, lambda buf: self._got_buf(data, buf))

    def _got_buf(self, data, buf):
        data.setContent(buf)
        self.sendFinish(data)


if __name__ == '__main__':
    from gi.repository import GLib
    import re

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name")
    parser.add_argument("url")

    args = parser.parse_args()
    if args.name:
        name = args.name
    else:
        name = re.sub('https?://', '', args.url)

    producer = Producer(name, args.url, auto=True)

    GLib.MainLoop().run()
