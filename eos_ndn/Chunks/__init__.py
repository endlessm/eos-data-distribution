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
import os

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GObject
from gi.repository import GLib

from pyndn import Name, Data, MetaInfo, ContentType

from .. import NDN
from ..NDN import Endless

logger = logging.getLogger(__name__)


def get_chunk_component(name):
    # The chunk component of a name is the last part...
    return name.get(-1)


class Producer(NDN.Producer):
    __gsignals__ = {'progress': (GObject.SIGNAL_RUN_FIRST, None, (int, )), 'complete': (GObject.SIGNAL_RUN_FIRST, None, (int, ))}

    def __init__(self, name, filename=None, chunkSize=4096, mode="r", size=None, *args, **kwargs):
        if size:
            self.size = size
        elif not filename:
            logger.critical('need to provide a size or filename argument: %s', name)
            raise ValueError
        else:
            self.size = os.path.getsize(filename)

        super(Producer, self).__init__(name=name, *args, **kwargs)
        self.chunkSize = chunkSize

        if filename:
            self.f = open(filename, mode)

        self.connect('interest', self.onInterest)

    def _getChunk(self, n):
        pos = self.chunkSize * n
        if pos >= self.size:
            self.emit('complete', self.size)
            logger.debug('asked for a chunk outside of file: %d, %d', pos, self.size)
            return False

        self.emit('progress', pos * 100 / self.size)

        self.f.seek(pos)
        return self.f.read(self.chunkSize)

    def sendChunk(self, data, n):
        content = self._getChunk(n)
        if content is None:
            data.setType(ContentType.NACK)
        else:
            data.setContent(content)
        self.sendFinish(data)

    def onInterest(self, o, prefix, interest, face, interestFilterId, filter):
        # Make and sign a Data packet.
        name = interest.getName()

        chunk_component = get_chunk_component(name)
        if chunk_component.isSegment():
            # If we have a segment component, then the client is asking for
            # a specific chunk here.
            seg = chunk_component.toSegment()
        else:
            # If not, then the user is asking for the barebones file. Return
            # to them the first segment.
            seg = 0
            name.appendSegment(seg)

        final_block_id = self.size / self.chunkSize
        meta_info = MetaInfo()
        meta_info.setFinalBlockId(Name.Component.fromSegment(final_block_id))
        data = Data(name)
        data.setMetaInfo(meta_info)

        logger.debug('got interest: %s, %d/%d', name, seg, final_block_id)

        self.sendChunk(data, seg)


class Consumer(NDN.Consumer):
    __gsignals__ = {'progress': (GObject.SIGNAL_RUN_FIRST, None, (int, )), 'complete': (GObject.SIGNAL_RUN_FIRST, None, (str, ))}

    def __init__(self, name, filename, chunkSize=4096, mode=os.O_CREAT | os.O_WRONLY | os.O_NONBLOCK, *args, **kwargs):
        super(Consumer, self).__init__(name=name, *args, **kwargs)

        try:
            os.makedirs(os.path.dirname(filename))
        except:
            pass

        if filename:
            self.filename = filename
            self.f = os.open(filename, mode)

        logger.debug('creating consumer: %s, %s', name, filename)

        self.chunkSize = chunkSize

        self.connect('data', self.onData)

    def consume(self, name=None, start=0, *args, **kwargs):
        if not name: name = self.name
        self.expressInterest(name=Name(name), forever=True, *args, **kwargs)

    def saveChunk(self, n, data):
        buf = data.getContent().toBuffer()
        start = self.chunkSize * n
        s = os.lseek(self.f, start, os.SEEK_SET)
        return os.write(self.f, buf)

    def onData(self, o, interest, data):
        meta_info = data.getMetaInfo()
        final_block_id = meta_info.getFinalBlockId().toSegment()

        name = data.getName()
        logger.debug('got data: %s', name)

        seg = get_chunk_component(name).toSegment()
        self.saveChunk(seg, data)

        self.emit('progress', float(seg / final_block_id) * 100)

        if seg < final_block_id:
            next_chunk = name.getSuccessor()
            self.expressInterest(next_chunk, forever=True)
        else:
            os.close(self.f)
            self.emit('complete', self.filename)
            logger.debug('fully retrieved: %s', self.filename)
