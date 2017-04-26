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

import errno
import json
import logging
import os
from shutil import copyfile
from os import path

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

from . import base

logger = logging.getLogger(__name__)

IFACE_TEMPLATE = '''<node>
<interface name='%s.%s'>
<method name='RequestInterest'>
    <arg type='s' direction='in'  name='name' />
    <arg type='h' direction='in'  name='fd' />
    <arg type='i' direction='in'  name='first_segment' />
    <arg type='i' direction='out' name='final_segment' />
</method>
<signal name='progress'>
    <arg type='s' direction='out' name='name' />
    <arg type='i' direction='out' name='first_segment' />
    <arg type='i' direction='out' name='last_segment' />
</signal>
</interface>
</node>'''

# signals -> property notification
# kill temporal signal
# only multiplex on the object path

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

    def setContent(self, buf):
        cur_pos = self.fd.tell()
        n = self.n + 1

        assert(cur_pos/base.CHUNK_SIZE == n)

        # write directly to the fd, sendFinish is a NOP
        logger.debug('write data START: %d, fd: %d, buf: %d',
                     n, cur_pos, len(buf))
        ret = self.fd.write(buf)
        self.fd.flush()
        logger.debug('write data END: %d, fd: %d', n, self.fd.tell())
        self.n = n
        return ret


class Consumer(base.Consumer):

    def __init__(self, name, *args, **kwargs):
        self.filename = None
        self.fd = None

        self.first_segment = 0
        self.current_segment = 0
        self._final_segment = None
        self._num_segments = None
        self._segments = None
        self._qualified_name = None
        self._emitted_complete = False

        super(Consumer, self).__init__(name=name, *args, **kwargs)
        logger.info('init DBUS chunks.Consumer: %s', name)

    def _dbus_express_interest(self, interest, dbus_path, dbus_name):
        # XXX parse interest to see if we're requesting the first chunk
        self.first_segment = 0
        self.interest = interest

        # XXX this comes from the original consumer implementation, not sure
        # we actually need them

        assert(not self.filename)
        assert(not self.fd)

        # we prepare the file where we're going to write the data
        self.filename = '.edd-file-cache-' + interest.replace('/', '%')
        self.fd = open(self.filename, 'w+b')

        logger.info('calling on; %s %s', dbus_path, dbus_name)

        args = GLib.Variant('(shi)', (interest, self.fd.fileno(), self.first_segment))
        self.con.call(dbus_name, dbus_path, dbus_name, 'RequestInterest',
                      args, None, Gio.DBusCallFlags.NONE, -1, None,
                      self._on_call_complete)
        self.con.signal_subscribe(None, dbus_name, 'progress', dbus_path, None, Gio.DBusSignalFlags.NO_MATCH_RULE, self._on_progress)
        self.con.signal_subscribe(None, dbus_name, 'complete', dbus_path, None, Gio.DBusSignalFlags.NO_MATCH_RULE, self._on_dbus_complete)

    def _save_chunk(self, n, data):
        raise NotImplementedError()

    def _on_progress(self, con, sender, path, interface, signal_name, parameters):
        name, first_segment, last_segment = parameters.unpack()
        logger.info('got progress, (%s) %s → %s', self.fd,  self.current_segment, last_segment)

        assert(self._final_segment)
        assert(first_segment <= self.current_segment)

        self.current_segment = max(self.current_segment, self.first_segment)
        self.fd.seek(self.current_segment * self.chunk_size)
        while (self.current_segment <= last_segment):
            progress = (float(self.current_segment) / (self._final_segment or 1)) * 100
            self.emit('progress', progress)
            logger.info('consumer read segment: %s', self.current_segment)
            buf = self.fd.read(self.chunk_size)
            if not buf:
                # XXX should we retry ?
                logger.info('consumer read segment FAILED: %s @ %s', self.current_segment, self.fd.tell())
                return

            self._save_chunk(self.current_segment, buf)
            self.current_segment += 1

        self.current_segment -= 1
        # XXX this would be self._check_for_complete()
        self._on_complete()

    def _on_call_complete(self, source, res):
        self._final_segment, = self.con.call_finish(res).unpack()

    def _on_dbus_complete(self, con, sender, path, interface, signal_name, parameters):
        # XXX name is probably not needed as we have a consumer ↔ producer
        # binding, via dbus sender address
        name, final_segment = parameters.unpack()
        self._final_segment = final_segment
        if self.current_segment < self._final_segment:
            self._wants_complete = True
            return

        return self._on_complete()

    def _on_complete(self):
        logger.debug("COMPLETE: %s, %s", self.current_segment, self._final_segment)
        assert (self.current_segment == self._final_segment)
        self.emit('complete')
        os.unlink(self.fd.name)
        self.fd.close()
        logger.debug('fully retrieved: %s', self.name)


    def _check_for_complete(self):
        # XXX we're not using this yet
        if self._segments.count(SegmentState.COMPLETE) == len(self._segments):
            if not self._emitted_complete:
                self._emitted_complete = True
                self._on_complete()
            else:
                logger.debug('Prevented emitting repeated complete signal')

    def _check_final_segment(self, n):
        if self._final_segment is not None:
            if n == self._final_segment:
                return
            else:
                raise ValueError("Could not read final segment")
        else:
            self._set_final_segment(n)

    def _on_data(self, o, interest, data):
        # XXX we're not using this yet
        self._num_outstanding_interests -= 1

        # If we get a NACK, then check for completion.
        meta_info = data.getMetaInfo()
        if meta_info.getType() == ContentType.NACK:
            self._check_for_complete()
            return

        self._check_final_segment(meta_info.getFinalBlockId().toSegment())

        name = data.getName()
        logger.debug('got data: %s', name)

        if self._qualified_name is None:
            # Strip off the chunk component for our final FQDN...
            # XXX: We should probably have a better parsing algorithm at some point
            # rather than relying on the chunk component being last.
            self._qualified_name = name.getPrefix(-1)

        seg = get_chunk_component(name).toSegment()

        # Have we somehow already got this segment?
        if self._segments[seg] == SegmentState.COMPLETE:
            logger.debug('Ignoring data ‘%s’ as it’s already been received',
                         name)
            self._check_for_complete()
            return

        # If saving the chunk fails, it might be because the chunk was invalid,
        # or is being deferred.
        if not self._save_chunk(seg, data):
            return
        self._segments[seg] = SegmentState.COMPLETE

        num_complete_segments = self._segments.count(SegmentState.COMPLETE)
        self.emit(
            'progress', (float(num_complete_segments) / len(self._segments)) * 100)

        self._schedule_interests()

class Producer(Base):
    __gsignals__ = {
        'register-failed': (GObject.SIGNAL_RUN_FIRST, None, (object, )),
        'register-success': (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        'interest': (GObject.SIGNAL_RUN_FIRST, None, (object, object, object, object, object))
    }

class Producer(base.Producer):
    def __init__(self, name, *args, **kwargs):
        super(Producer, self).__init__(name=name,
                                       iface_template=IFACE_TEMPLATE,
                                       *args, **kwargs)

    def impl_RequestInterest(self, connection, sender, object_path, interface_name, method_name, parameters, invocation):
        name, fd, first = parameters.unpack()

        # do we start on chunk 0 ? full file ? do we start on another chunk
        # ? we need to seek the file, subsequent calls to get the same
        # chunks have to be handled in the consumer part and folded into
        # answering to only one dbus call

        final_segment = self._get_final_segment()
        if not final_segment:
            raise NotImplementedError()

        self._workers[name] = worker = ProducerWorker(fd, first, final_segment, self._send_chunk)
        invocation.return_value(GLib.Variant('(i)', (final_segment,)))

        # XXX: is this racy ?
        GLib.timeout_add_seconds(5,
            lambda: self.con.emit_signal(sender, object_path,
                                        interface_name, 'progress',
                                        GLib.Variant('(sii)', (name, worker.first_segment, worker.data.n))) or True)

    def sendFinish(self, data):
        # we don't need to do anything here because we write the file in
        # setContent, we don't do it here because that would require us to
        # cache big chunks of data in memory.
        pass

class ProducerWorker():
    def __init__(self, fd, first_segment, final_segment, send_chunk):
        self.first_segment = first_segment
        self.current_segment = first_segment
        self.fd = os.fdopen(fd, 'w+b')
        self.data = Data(self.fd, first_segment)

        logger.info('start segments: %s, %s', self.current_segment, final_segment)
        while(True):
            send_chunk(self.data, self.current_segment)
            if self.current_segment < final_segment:
                self.current_segment += 1
            else:
                break

        logger.info('end segments: %s, %s', self.current_segment, final_segment)

if __name__ == '__main__':
    import re
    from .tests import utils
    from . import http

    parser = utils.process_args()
    parser.add_argument("-c", "--cost", default=10)
    parser.add_argument("-o", "--output", default='test.shard')
    parser.add_argument("url")
    args = parser.parse_args()

    if args.name:
        name = args.name
    else:
        name = re.sub('https?://', '', args.url)

    consumer = http.Consumer(name=name, url=args.url)
    utils.run_consumer_test(consumer, name, args)
