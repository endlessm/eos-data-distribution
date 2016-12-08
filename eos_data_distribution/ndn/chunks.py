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

from . import base

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

    def __init__(self, name, chunk_size=CHUNK_SIZE, pipeline=5, *args, **kwargs):
        self.chunk_size = chunk_size
        self._total_interest_requests = pipeline
        self._final_segment = None
        self._num_outstanding_interests = 0
        self._total_retrieved_segments = 0
        self._last_sent_segment = 0

        super(Consumer, self).__init__(name=name, *args, **kwargs)
        self.connect('data', self._on_data)

    def consume(self):
        self.expressInterest(name=self.name, forever=True)
        self._num_outstanding_interests += 1

    def _save_chunk(self, n, data):
        pass

    def _on_complete(self):
        self.emit('complete')
        logger.debug('fully retrieved: %s', self.name)

    def _check_for_complete(self):
        # If we have no outstanding interests, and we've retrieved enough segments,
        # then we're complete.
        total_num_segments = self._final_segment + 1
        if self._num_outstanding_interests == 0 and self._total_retrieved_segments == total_num_segments:
            self._on_complete()

    def _schedule_interests(self):
        while self._num_outstanding_interests < self._total_interest_requests:
            next_segment = self._last_sent_segment + 1

            if next_segment > self._final_segment:
                self._check_for_complete()
                return

            ndn_name = Name(self.name).appendSegment(next_segment)
            self.expressInterest(ndn_name, forever=True)
            self._num_outstanding_interests += 1
            self._last_sent_segment += 1

    def _on_data(self, o, interest, data):
        self._num_outstanding_interests -= 1

        # If we get a NACK, then check for completion.
        meta_info = data.getMetaInfo()
        if meta_info.getType() == ContentType.NACK:
            self._check_for_complete()
            return

        self._final_segment = meta_info.getFinalBlockId().toSegment()

        name = data.getName()
        logger.debug('got data: %s', name)

        seg = get_chunk_component(name).toSegment()
        self._save_chunk(seg, data)
        self._total_retrieved_segments += 1

        total_num_segments = self._final_segment + 1
        self.emit('progress', (float(self._total_retrieved_segments) / total_num_segments) * 100)

        self._schedule_interests()
