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

from gi.repository import GObject

from pyndn import Name, Data, MetaInfo, ContentType

from . import base, Endless

logger = logging.getLogger(__name__)

CHUNK_SIZE = 4096

def get_chunk_component(name):
    # The chunk component of a name is the last part...
    return name.get(-1)


class Producer(base.Producer):
    def __init__(self, name, chunk_size=CHUNK_SIZE, *args, **kwargs):
        super(Producer, self).__init__(name=name, *args, **kwargs)
        self.chunk_size = chunk_size
        self.connect('interest', self._on_interest)

    def _get_final_block_id(self):
        pass

    def _send_chunk(self, data, n):
        content = self._get_chunk(n)
        if content is None:
            data.getMetaInfo().setType(ContentType.NACK)
        else:
            data.setContent(content)
        self.sendFinish(data)

    def _on_interest(self, o, prefix, interest, face, interestFilterId, filter):
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

        final_block_id = self._get_final_block_id()
        meta_info = MetaInfo()
        meta_info.setFinalBlockId(Name.Component.fromSegment(final_block_id))
        data = Data(name)
        data.setMetaInfo(meta_info)

        logger.debug('got interest: %s, %d/%d', name, seg, final_block_id)

        self._send_chunk(data, seg)


class Consumer(base.Consumer):
    __gsignals__ = {
        'progress': (GObject.SIGNAL_RUN_FIRST, None, (int, )),
        'complete': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, name, chunk_size=CHUNK_SIZE, *args, **kwargs):
        super(Consumer, self).__init__(name=name, *args, **kwargs)
        self.chunk_size = chunk_size
        self.connect('data', self._on_data)

    def consume(self, name=None, *args, **kwargs):
        if not name: name = self.name
        self.expressInterest(name=Name(name), forever=True, *args, **kwargs)

    def _save_chunk(self, n, data):
        pass

    def _on_data(self, o, interest, data):
        meta_info = data.getMetaInfo()
        final_block_id = meta_info.getFinalBlockId().toSegment()

        name = data.getName()
        logger.debug('got data: %s', name)

        seg = get_chunk_component(name).toSegment()
        self._save_chunk(seg, data)

        self.emit('progress', float(seg / final_block_id) * 100)

        if seg < final_block_id:
            next_chunk = name.getSuccessor()
            self.expressInterest(next_chunk, forever=True)
        else:
            self.emit('complete')
            logger.debug('fully retrieved: %s', self.name)
