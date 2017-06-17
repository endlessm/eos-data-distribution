# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2017 Endless Mobile Inc.
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
from os import path

import gi
gi.require_version('EosDataDistributionDbus', '0')
gi.require_version('GLib', '2.0')

from gi.repository import EosDataDistributionDbus
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

from . import base
from ... import defaults
from .base import Interest
from eos_data_distribution import utils
from eos_data_distribution.names import Name

logger = logging.getLogger(__name__)

CHUNKS_DBUS_NAME = 'com.endlessm.NDNHackBridge.chunks'

# signals -> property notification
# kill temporal signal
# only multiplex on the object path

def get_chunkless_name(name):
    """
    We don't ever generate chunked names in this implementation
    """
    return name

class Data(object):
    """Data:

    This mimics the NDN Data object, it should implement as little API as we
    need, we pass an fd that comes from the Consumer, and currently
    setContent is a hack that actually writes to the fd.
    we write here so that we don't have to cache big chunks of data in memory.

    """
    def __init__(self, fd, n = 0):
        super(Data, self).__init__()

        self.fd = fd
        self.n = n - 1
        self.fd.seek(n*base.CHUNK_SIZE)

    def setName(self, name):
        # we have nothing to see here
        pass

    def setMetaInfo(self, info):
        # we don't implement this
        pass

    def setContent(self, buf):
        cur_pos = self.fd.tell()
        n = self.n + 1

        logger.debug('write data START: %d, fd: %d', n, cur_pos)
        assert(cur_pos/base.CHUNK_SIZE == n)

        # write directly to the fd, sendFinish is a NOP
        ret = self.fd.write(buf)
        self.fd.flush()

        self.n = n
        return ret


class Consumer(base.Consumer):

    def __init__(self, name, *args, **kwargs):
        self.filename = None
        self.fd = None
        self.sendout_fd = None

        self.first_segment = 0
        self.current_segment = 0
        self._final_segment = None
        self._num_segments = None
        self._segments = []
        self._qualified_name = None
        self._emitted_complete = False
        self._interface = None

        super(Consumer, self).__init__(name=name,
                                       dbus_name=CHUNKS_DBUS_NAME,
                                       object_manager_class=EosDataDistributionDbus.ChunksObjectManagerClient,
                                       *args, **kwargs)

        logger.info('init DBUS chunks.Consumer: %s', name)

    def _do_express_interest(self, proxy, interface, interest):
        # first we request the version, that will allow to check if we have
        # an early resolution and not allocate ressources on the other side
        # for nothing.
        return interface.call_discover_version(
            interest, callback=self._on_discover_version_complete,
            user_data=interest)

    def _on_discover_version_complete(self, interface, res, interest):
        name, final_segment = interface.call_discover_version_finish(res)
        # XXX: order here is important as we check for complete in setName()
        self._set_final_segment(final_segment)
        self.setName(name)

        self._interface = interface
        if self._check_for_complete():
            return # early return if we completed in the init

        # XXX parse interest to see if we're requesting the first chunk
        try:
            self.current_segment = self.first_segment = self._segments.index(defaults.SegmentState.UNSENT)
        except ValueError, AttributeError:
            self.current_segment = self.first_segment = 0

        logger.debug('STARTING AT %s', self.first_segment)
        self.interest = interest

        if self.filename:
            # did we already have an open file descriptor for this ? if yes,
            # we'd better close it here and reopen so that we're sure we get
            # a fresh fd.
            logger.debug('already had fd %s, %s', self.fd, self.sendout_fd)

            self.fd.close()
            if self.sendout_fd:
                self.sendout_fd.close()

        # we prepare the file where we're going to write the data
        self.filename = '.edd-file-cache-' + interest.replace('/', '%')
        self.sendout_fd = open(self.filename, 'w+b')
        self.fd = open(self.filename, 'r+b')


        logger.debug('opened fd: %s', self.fd)

        fd_list = Gio.UnixFDList()
        fd_id = fd_list.append(self.sendout_fd.fileno())

        assert(self.filename)
        assert(self.fd)

        interface.connect('progress', self._on_progress)
        interface.call_request_interest(interest,
                                        GLib.Variant('h', fd_id),
                                        self.first_segment, fd_list=fd_list,
                                        callback=self._on_request_interest_complete,
                                        user_data=interest)

    def _save_chunk(self, n, data):
        raise NotImplementedError()

    def _on_progress(self, proxy, name, first_segment, last_segment):
        if not self._final_segment:
            return # still initing come back later

        if self._emitted_complete:
            return # all finished don't do anything

        segment_table_size = len(self._segments)
        logger.info('got progress, %s → %s (%s:%s)',
                     self.current_segment, last_segment, self._final_segment, segment_table_size)

        self.current_segment = max(self.current_segment, self.first_segment)
        if self._final_segment < last_segment:
            logger.info('We got a new size ! expanding segments !')
            self._final_segment = last_segment
            self._segments = self._segments[:self.current_segment]
            self._segments.extend(
                [defaults.SegmentState.OUTGOING]*(self._final_segment - self.current_segment))
            logger.info('new size: %s', len(self._segments))

        else:
            for n in xrange(self.current_segment, last_segment):
                self._segments[n] = defaults.SegmentState.OUTGOING

        assert(self._final_segment != None)
        assert(first_segment <= self.current_segment)
        assert(last_segment <= self._final_segment)

        if self._emitted_complete:
            logger.debug('COMPLETE already emitted for %s', name)
            return

        self.fd.seek(self.current_segment * self.chunk_size)

        while (self.current_segment <= last_segment):
            progress = (float(self.current_segment) / (self._final_segment or 1)) * 100
            self.emit('progress', progress)
            logger.debug('consumer read segment: %s', self.current_segment)
            buf = self.fd.read(self.chunk_size)
            if not buf:
                # XXX should we retry ?
                logger.warning('consumer read segment FAILED: %s @ %s', self.current_segment, self.fd.tell())
                return

            self._save_chunk(self.current_segment, buf)
            self._segments[self.current_segment] = defaults.SegmentState.COMPLETE
            self.current_segment += 1

        self.current_segment -= 1
        self._complete()

    def _complete(self):
        if not self._emitted_complete:
            self._emitted_complete = True
            self._interface.call_complete(
                str(self.name), callback=self._on_complete)

    def _request_interest_complete(self, interface, res, interest):
        logger.info('Consumer: request interest complete: %s, %s, %s', interface, res, interest)
        name, final_segment, fd_list = interface.call_request_interest_finish(res)

    def _set_final_segment(self, n):
        self._final_segment = n
        self._num_segments = self._final_segment + 1
        self._size = self.chunk_size * self._num_segments

        if len(self._segments) == 0:
            self._segments = [defaults.SegmentState.UNSENT] * self._num_segments

    def _check_final_segment(self, n):
        if self._final_segment is not None:
            if n == self._final_segment:
                return
            else:
                raise ValueError("Could not read final segment")
        else:
            self._set_final_segment(n)

    def _check_for_complete(self):
        return self.current_segment == self._final_segment

    def _on_complete(self, *args, **kwargs):
        logger.debug("COMPLETE: %s, %s, %s", self.name, self.current_segment, self._final_segment)
        assert (self.current_segment == self._final_segment)
        self.emit('complete')
        if self.fd: # may have never opened it
            os.unlink(self.fd.name)
            self.fd.close()
        logger.info('fully retrieved: %s', self.name)

class Producer(base.Producer):
    def __init__(self, name, *args, **kwargs):
        self._workers = dict()

        super(Producer, self).__init__(name=name,
                                       dbus_name=CHUNKS_DBUS_NAME,
                                       skeleton=EosDataDistributionDbus.ChunksChunksProducerSkeleton,
                                       *args, **kwargs)

    def _get_final_segment(self):
        raise NotImplementedError

    def _send_chunk(self, data, n):
        content = self._get_chunk(n)
        if content is None:
            # we don't really support NACKs, log an error and return
            raise NotImplementedError("got NACK but we don't support it !")
            #data.getMetaInfo().setType(ContentType.NACK)
        else:
            data.setContent(content)

        self.sendFinish(data)

    def _on_discover_version(self, name, skeleton):
        try:
            final_segment = self._get_final_segment()
        except NotImplementedError:
            logger.debug("we can't handle this, let another producer come in and do it.")
            return self._dbus.return_error(name, 'ETRYAGAIN')
        # do we start on chunk 0 ? full file ? do we start on another chunk
        # ? we need to seek the file, subsequent calls to get the same
        # chunks have to be handled in the consumer part and folded into
        # answering to only one dbus call

        key = name.toString()
        try:
            worker = self._workers[key]
            logger.debug('already got a worker for name %s', self.name)
            return self._dbus.return_error(name, 'ETOOMANY')
        except KeyError:
            pass

        self._workers[key] = worker = ProducerWorker(final_segment)
        skeleton, invocation, fd_list = self._dbus._obj_registery[key]
        self._dbus._return_value('discover_version', name, final_segment)

    def _on_request_interest(self, name, skeleton, fd_list, fd_variant, first_segment):
        self.emit('interest', self.name, Interest(name), None, None, None)
        fd = fd_list.get(fd_variant.get_handle())
        logger.debug('RequestInterest Handler: name=%s, self.name=%s, fd=%d, first_segment=%d',
                     name, self.name, fd, first_segment)
        key = name.toString()
        worker = self._workers[key]
        last_emited = first_segment - 1
        # XXX: is this racy ?
        GLib.timeout_add_seconds(5,
            lambda: (worker.data.n > last_emited and
                                 skeleton.emit_progress(key, worker.first_segment,
                                                        worker.data.n)) or worker.working)
        worker.start(fd, first_segment, self._send_chunk)
        self._dbus.return_value(name, worker.final_segment)
        return True

    def _on_complete(self, name, skeleton):
        logger.debug('PRODUCER on_complete: %s', name)
        # remove worker from hash so it gets freed, we close here too as we
        # get another fd from the consumer
        key = name.toString()
        worker = self._workers[key]
        worker.working = False
        try:
            worker.fd.close()
        except AttributeError:
            pass
        del self._workers[key]
        return True

    def sendFinish(self, data):
        # we don't need to do anything here because we write the file in
        # setContent, we don't do it here because that would require us to
        # cache big chunks of data in memory.
        pass

class ProducerWorker():
    def __init__(self, final_segment):
        logger.info('Spawning NEW ProducerWorker: %s', final_segment)
        self.working = True
        self.final_segment = final_segment

    def start(self, fd, first_segment, send_chunk):
        self.first_segment = self.current_segment = first_segment
        self.fd = os.fdopen(fd, 'w+b')
        self.data = Data(self.fd, self.first_segment)

        while(True):
            send_chunk(self.data, self.current_segment)
            if self.current_segment < self.final_segment:
                self.current_segment += 1
            else:
                break

        logger.info('end segments: %s, %s', self.current_segment, self.final_segment)

if __name__ == '__main__':
    import re
    from .tests import utils as testutils
    from . import http

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cost", default=10)
    parser.add_argument("-o", "--output", default='test.shard')
    parser.add_argument("url")
    args = utils.parse_args(parser=parser)

    if args.name:
        name = args.name
    else:
        name = re.sub('https?://', '', args.url)

    consumer = http.Consumer(name=name, url=args.url)
    testutils.run_consumer_test(consumer, name, args)
