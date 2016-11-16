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

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GObject
from gi.repository import GLib

from pyndn import Name
from pyndn import Data

import NDN
from NDN import Endless

import logging
logging.basicConfig(level=Endless.LOGLEVEL)
logger = logging.getLogger(__name__)

class Producer(NDN.Producer):
    def __init__(self, name, filename=None, chunkSize=4096, mode="r",
                 *args, **kwargs):
        super(Producer, self).__init__(name=name, *args, **kwargs)
        self.chunkSize = chunkSize

        if filename:
            self.f = open(filename, mode)

        self.connect('interest', self.onInterest)

    def getChunk(self, name, n, prefix=None):
        logger.debug('asked for chunk %d: %s', n, NDN.dumpName(name))
        self.f.seek(self.chunkSize * n)
        return self.f.read(self.chunkSize)

    def onInterest(self, o, prefix, interest, face, interestFilterId, filter):
        # Make and sign a Data packet.
        name = interest.getName()
        logger.debug ('got interest: %s', name)
        # hack to get the segment number
        seg = int(repr(name).split('%')[-1], 16)

        content = self.getChunk(name, seg, prefix=prefix)
        self.send(name, content)

class Consumer(NDN.Consumer):
    def __init__(self, name, filename, chunkSize = 4096, mode = "w+", pipeline=5, *args, **kwargs):
        super(Consumer, self).__init__(name=name, *args, **kwargs)
        if filename:
            self.f = open(filename, mode)

        logger.debug ('creating consumer: %s, %s', name, filename)

        self.pipeline = pipeline
        self.chunkSize = chunkSize

        self.connect('data', self.onData)

    def consume(self, name=None, start=0, *args, **kwargs):
        if not name: name = self.name
        self.expressInterest(name=Name(name).appendSegment(0), *args, **kwargs)

    def putChunk(self, n, data):
        buf = self.dataToBytes(data)

        logger.debug('getting chunk %d: %d: %s', n, self.chunkSize, self.f)
        self.f.seek(self.chunkSize * n)
        return self.f.write(buf)

    def onData(self, o, interest, data):
        name = data.getName()
        logger.debug('got data: %s', NDN.dumpName(name))
        seg = int(name.toUri().split('%')[-1], 16)
        self.putChunk(seg, data)

        reduce (lambda n, r: self.getNext(n), range(self.pipeline), name)
        self.getNext(name)

    def getNext(self, name):
        suc = name.getSuccessor()
        logger.debug('get Next %s → %s', NDN.dumpName(name), NDN.dumpName(suc))
        self.expressInterest(suc)
        return suc

