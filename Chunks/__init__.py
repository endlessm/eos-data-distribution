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

import NDN
from NDN import Endless

import os

import logging
logging.basicConfig(level=Endless.LOGLEVEL)
logger = logging.getLogger(__name__)

def getSeg (name):
    seg = name.get(-1)
    if str (seg) == 'chunked':
        return -1
    return seg.toNumber ()

def appendSize (name, size):
    return name.append ('size=%s'%hex (size))

def getSize (name):
    s = name.get (-2)
    return int (str (s).split ('size%3D') [1], 16)

class Producer(NDN.Producer):
    __gsignals__ = {
        'progress': (GObject.SIGNAL_RUN_FIRST, None,
                     (int,)),
        'complete': (GObject.SIGNAL_RUN_FIRST, None,
                     (int,))
    }

    def __init__(self, name, filename=None, chunkSize=4096, mode="r",
                 size=None, *args, **kwargs):
        if size:
            self.size = size
        elif not filename:
            logger.critical ('need to provide a size or filename argument: %s', name)
            raise ValueError
        else:
            self.size = os.path.getsize (filename)

        name = Name (name).append ('chunked')
        super(Producer, self).__init__(name=name, *args, **kwargs)
        appendSize (self.name, self.size)
        self.chunkSize = chunkSize

        if filename:
            self.f = open(filename, mode)

        self.connect('interest', self.onInterest)

    def getChunk(self, name, n, prefix=None):
        logger.debug('asked for chunk %d: %s', n, NDN.dumpName(name))
        pos = self.chunkSize * n
        if pos >= self.size:
            self.emit ('complete', self.size)
            logger.debug ('asked for a chunk outside of file: %d, %d', pos, self.size)
            return False

        self.emit ('progress', pos*100/self.size)

        self.f.seek(pos)
        return self.f.read(self.chunkSize)

    def onInterest(self, o, prefix, interest, face, interestFilterId, filter):
        # Make and sign a Data packet.
        name = interest.getName()
        # hack to get the segment number
        seg = getSeg (name)
        if seg == -1:
            seg = 0
            appendSize (name, self.size)
            name.appendSegment (0)

        logger.debug ('got interest: %s, %d/%d', name, seg, self.size/self.chunkSize)

        content = self.getChunk(name, seg, prefix=prefix)
        if content == True:
            return
        if content == False:
            return self.nack (name)

        return self.send(name, content)

class Consumer(NDN.Consumer):
    __gsignals__ = {
        'progress': (GObject.SIGNAL_RUN_FIRST, None,
                     (int,)),
        'complete': (GObject.SIGNAL_RUN_FIRST, None,
                     (str,))
    }

    def __init__(self, name, filename, chunkSize = 4096, mode = "w+", pipeline=5,
                 *args, **kwargs):
        name = Name (name).append ('chunked')
        super(Consumer, self).__init__(name=name, *args, **kwargs)

        try:
            os.makedirs (os.path.dirname (filename))
        except:
            pass

        if filename:
            self.filename = filename
            self.f = open(filename, mode)

        logger.debug ('creating consumer: %s, %s', name, filename)

        self.size = None
        self.got = 0
        self.pipeline = pipeline
        self.chunkSize = chunkSize

        self.connect('data', self.onData)

    def consume(self, name=None, start=0, *args, **kwargs):
        if not name: name = self.name
        self.expressInterest(name=Name(name), forever=True, *args, **kwargs)

    def putChunk(self, n, data):
        buf = self.dataToBytes(data)

        logger.debug('writing chunk %d/%d', n, self.size/self.chunkSize)
        start = self.chunkSize * n
        s = self.f.seek(start)
        self.f.write(buf)
        return self.f.tell () - start

    def onData(self, o, interest, data):
        name = data.getName()
        logger.debug('got data: %s', NDN.dumpName(name))
        seg = getSeg (name)
        if not self.size:
            self.size = getSize (name)
            print 'size', self.size

        #TODO: write async
        suc = self.getNext (name)
        self.got += self.putChunk (seg, data)

        self.emit ('progress', self.got*100/self.size)

        if self.got >= self.size:
            self.f.close ()
            self.emit ('complete', self.filename)
            logger.debug ('fully retrieved: %d', self.size)
            self.removePendingInterest (suc)

    def getNext(self, name):
        suc = name.getSuccessor()
        logger.debug('get Next %s → %s', name, suc)
        self.expressInterest(suc, forever=True)
        return suc

