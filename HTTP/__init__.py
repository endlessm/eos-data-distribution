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

import Chunks

import gi
gi.require_version('Soup', '2.4')

from gi.repository import Soup

from NDN import Endless

from functools import partial

import logging
logging.basicConfig(level=Endless.LOGLEVEL)
logger = logging.getLogger(__name__)

def makeSession ():
    session = Soup.Session ()
    session.props.ssl_strict = False
    session.props.max_conns = 100
    session.props.max_conns_per_host = 100

    return session

class Producer (Chunks.Producer):
    def __init__(self, name, url, session = None,
                 *args, **kwargs):
        self.url = url
        
        self.session = session
        if not self.session:
            self.session = makeSession ()

        try:
            size = kwargs['size']
        except:
            # go out make a request to get size
            msg = Soup.Message.new ("GET", url)
            msg.request_headers.append ('Range', 'bytes=0-0')
            self.session.send (msg, None)
            CR = msg.response_headers.get_one ('Content-Range')
            size = int (CR.split ('/') [1])

        super(Producer, self).__init__(name, size=size, *args, **kwargs)

    def getChunk(self, name, n, prefix):
        logger.debug ('asked for %s: %s (%d)', name, prefix, n)

        self.soupGet (name, n, self.url)
        return True

    def soupGet (self, name, n, uri):
        msg = Soup.Message.new ('GET', uri)
        bytes = (n*self.chunkSize, (n+1)*self.chunkSize - 1)
        msg.request_headers.append ('Range', 'bytes=%d-%d'%bytes)

        logger.info ('range %s', bytes)
        streamToData = partial (self.streamToData, name=name, n=n, msg=msg)
        self.session.send_async (msg, None, streamToData)
        return msg

    def streamToData (self, session, task, name, n, msg):
        s = msg.status_code
        if not (s == Soup.Status.OK or s == Soup.Status.PARTIAL_CONTENT):
            return False

        logger.info ('reply is: %s', msg.status_code)
        istream = session.send_finish (task)

        logger.info ('sending on name: %s', name)
        buf = istream.read_bytes(self.chunkSize, None).get_data()
        self.send(name, buf)

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
        name = re.sub ('https?://', '', args.url)

    producer = Producer (name, args.url, auto=True)

    GLib.MainLoop().run()

