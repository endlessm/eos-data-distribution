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

class Producer(NDN.Producer):
    def __init__(self, name, filename=None, chunkSize=4096, mode="r+",
                 *args, **kwargs):
        super(Producer, self).__init__(name=name, *args, **kwargs)
        self.chunkSize = chunkSize

        if filename:
            self.f = open(filename, mode)

        self.connect('interest', self.onInterest)

    def getChunk(self, name, n, prefix=None):
        print 'asked for chunk', n, name.toUri()
        self.f.seek(self.chunkSize * n)
        return self.f.read(self.chunkSize)

    def onInterest(self, o, prefix, interest, face, interestFilterId, filter):
        # Make and sign a Data packet.
        name = interest.getName()
        # hack to get the segment number
        seg = int(repr(name).split('%')[-1], 16)

        content = "%s;" % self.chunkSize
        content += self.getChunk(name, seg, prefix=prefix)
        self.send(name, content)

class Consumer(NDN.Consumer):
    def __init__(self, name, filename, chunkSize = 4096, mode = "w+", pipeline=5, *args, **kwargs):
        super(Consumer, self).__init__(name=name, *args, **kwargs)
        if filename:
            self.f = open(filename, mode)

        self.pipeline = pipeline
        self.chunkSize = chunkSize

        self.connect('data', self.onData)

    def consume(self, name=None, start=0, *args, **kwargs):
        if not name: name = self.name
        self.expressInterest(name=Name(name).appendSegment(0), *args, **kwargs)

    def putChunk(self, n, data):
        buf = self.dataToBytes(data)

        chunkSize = str(buf[:10]).split(';')[0]
        skip = len(chunkSize) + 1
        chunkSize = int(chunkSize)
        self.f.seek(chunkSize * n)
        return self.f.write(buf[skip:])

    def onData(self, o, interest, data):
        name = data.getName()
        seg = int(repr(name).split('%')[-1], 16)
        self.putChunk(seg, data)

        reduce (lambda n, r: self.getNext(n), range(self.pipeline), name)
        self.getNext(name)

    def getNext(self, name):
        suc = name.getSuccessor()
        print 'get Next', name.toUri(), suc.toUri()
        self.expressInterest(suc)
        return suc

