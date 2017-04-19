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

logging.basicConfig(level=logging.INFO)

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

from .. import defaults
from ..names import Name, SUBSCRIPTIONS_BASE

from .utils import singleton

logger = logging.getLogger(__name__)

CHUNK_SIZE = defaults.CHUNK_SIZE

BUS_TYPE = Gio.BusType.SESSION

BASE_DBUS_NAME = 'com.endlessm.NDNHackBridge'
BASE_DBUS_PATH = '/com/endlessm/NDNHackBridge'

DBUS_NAME_TEMPLATE = '%s.%s'
DBUS_PATH_TEMPLATE = '%s/%s'

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
    <arg type='i' direction='out' name='last_segment' />
</signal>
<signal name='completed'>
    <arg type='s' direction='out' name='name' />
    <arg type='i' direction='out' name='final_segment' />
</signal>
</interface>
</node>'''

@singleton
def get_name_registry():
    return dict()

def get_dbusable_name(base):
    if str(base).startswith(str(SUBSCRIPTIONS_BASE)):
        return SUBSCRIPTIONS_BASE[-1]
    else:
        return 'custom'

class Base(GObject.GObject):
    """Base class

    All this is a lie, we put here all the boilerplate code we need to have
    our clases behave like the real chunks

    """
    def __init__(self, name,
                 chunk_size=CHUNK_SIZE,
                 cost=defaults.RouteCost.DEFAULT):
        GObject.GObject.__init__(self)
        self.chunk_size = chunk_size
        self.cost = cost
        self.name = name


class Data(object):
    """Data:

    This mimics the NDN Data object, it should implement as little API as we
    need, we pass an fd that comes from the Consumer, and currently
    setContent is a hack that actually writes to the fd.
    we write here so that we don't have to cache big chunks of data in memory.

    """
    def __init__(self, fd):
        super(Data, self).__init__()

        self.fd = os.fdopen(fd, 'w+')

    def setContent(self, buf):
        # write directly to the fd, sendFinish is a NOP
        return self.fd.write(buf)


class Consumer(Base):
    __gsignals__ = {
        'progress': (GObject.SIGNAL_RUN_FIRST, None, (int, )),
        'complete': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, name, *args, **kwargs):
        self.con = None
        self.filename = None
        self.fd = None

        self.first_segment = 0
        self.current_segment = 0
        self._wants_start = False
        self._final_segment = None
        self._num_segments = None
        self._segments = None
        self._qualified_name = None
        self._emitted_complete = False

        super(Consumer, self).__init__(name=name, *args, **kwargs)
        dbusable_name = get_dbusable_name(name)
        dbus_name = DBUS_NAME_TEMPLATE % (BASE_DBUS_NAME, dbusable_name)
        Gio.bus_watch_name(BUS_TYPE, dbus_name,
                           Gio.BusNameWatcherFlags.AUTO_START,
                           self._name_appeared_cb,
                           self._name_vanished_cb)

        logger.info('init DBUS chunks.Consumer: %s → %s', name, dbus_name)

    def _name_appeared_cb(self, con, name, owner):
        logger.info('name: %s, appeared, owned by %s', name, owner)
        self.con = con
        if self._wants_start:
            self.start()
            self._wants_start = False

    def _name_vanished_cb(self, con, name):
        self.con = None

    def start(self):
        if not self.con:
            # come back when you have someone to talk too
            self._wants_start = True
            return

        if not self._segments:
            # Make an initial request for the barename. We should get a fully
            # qualified request back for the first segment, with a timestamp and
            # segment number. Future requests will request the fully qualified
            # name.
            self.expressInterest(try_again=True)
        else:
            self._schedule_interests()


    def expressInterest(self, interest=None, try_again=False):
        if not interest:
            interest = self.name

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

        dbusable_name = get_dbusable_name(interest)

        dbus_path = DBUS_PATH_TEMPLATE % (BASE_DBUS_PATH, dbusable_name)
        dbus_name = DBUS_NAME_TEMPLATE % (BASE_DBUS_NAME, dbusable_name)

        logger.info('calling on; %s %s', dbus_path, dbus_name)

        args = GLib.Variant('(shi)', (interest, self.fd.fileno(), self.first_segment))
        self.con.call(dbus_name, dbus_path, dbus_name, 'RequestInterest',
                      args, None, Gio.DBusCallFlags.NONE, -1, None,
                      self._on_call_complete, self.fd)
        self.con.signal_subscribe(None, dbus_name, 'progress', dbus_path, None, Gio.DBusSignalFlags.NO_MATCH_RULE, self._on_progress)
        self.con.signal_subscribe(None, dbus_name, 'complete', dbus_path, None, Gio.DBusSignalFlags.NO_MATCH_RULE, self._on_dbus_complete)

    def _save_chunk(self, n, data):
        raise NotImplementedError()

    def _on_progress(self, con, sender, path, interface, signal_name, parameters):
        name, last_segment = parameters.unpack()
        logger.info('got progress, %s', last_segment)

        assert(self._final_segment)

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

        # XXX this would be self._check_for_complete()
        self._on_complete()

    def _on_call_complete(self, source, res, fd):
        self._final_segment, = self.con.call_finish(res).unpack()

    def _on_dbus_complete(self, con, sender, path, interface, signal_name, parameters):
        name, final_segment = parameters.unpack()
        self._final_segment = final_segment
        if self.current_segment < self._final_segment:
            self._wants_complete = True
            return

        return self._on_complete()

    def _on_complete(self):
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

    def __init__(self, name, *args, **kwargs):
        self.registered = False

        super(Producer, self).__init__(name=name, *args, **kwargs)
        self.con = Gio.bus_get_sync(BUS_TYPE, None)

    def start(self):
        self.registerPrefix()

    def registerPrefix(self, prefix=None):
        if prefix:
            # XXX: prefix registeration is handled checking that the prefix
            # is a strict subname, but 'strict' is still to be defined
            logger.error("We don't support prefix registeration")
            raise NotImplementedError()

        dbusable_name = get_dbusable_name(self.name)

        dbus_path = DBUS_PATH_TEMPLATE % (BASE_DBUS_PATH, dbusable_name)
        dbus_name = DBUS_NAME_TEMPLATE % (BASE_DBUS_NAME, dbusable_name)
        iface_str =     IFACE_TEMPLATE % (BASE_DBUS_NAME, dbusable_name)
        iface_info= Gio.DBusNodeInfo.new_for_xml(iface_str).interfaces[0]

        if self.registered:
            console.error('already registered')
            return

        Gio.bus_own_name_on_connection(
            self.con, dbus_name, Gio.BusNameOwnerFlags.NONE, None, None)

        registered = self.con.register_object(
            object_path=dbus_path,
            interface_info=iface_info, method_call_closure=self._on_method_call)

        if not registered:
            logger.error('got error: %s, %s, %s, %s',
                         registered, dbus_name, dbus_path, iface_str)
            self.emit('register-failed', registered)

        logger.info('registred: %s, %s, %s',
                    dbus_name, dbus_path, iface_str)

        self.registered = True

    def _on_method_call(self, connection, sender, object_path, interface_name, method_name, parameters, invocation):
        # Dispatch.
        getattr(self, 'impl_%s' % (method_name, ))(connection, sender, object_path, interface_name, method_name, parameters, invocation)

    def impl_RequestInterest(self, connection, sender, object_path, interface_name, method_name, parameters, invocation):
        name, fd, first = parameters.unpack()

        # do we start on chunk 0 ? full file ? do we start on another chunk
        # ? we need to seek the file, subsequent calls to get the same
        # chunks have to be handled in the consumer part and folded into
        # answering to only one dbus call

        final_segment = self._get_final_segment()
        current_segment = first
        data = Data(fd)

        if not final_segment:
            raise NotImplementedError()

        # XXX: is this racy ?
        invocation.return_value(GLib.Variant('(i)', (final_segment,)))
        GLib.timeout_add_seconds(5,
            lambda: self.con.emit_signal(sender, object_path,
                                        interface_name, 'progress',
                                        GLib.Variant('(si)', (name, current_segment))) or True)
        logger.info('start segments: %s, %s', current_segment, final_segment)
        while (current_segment <= final_segment):
            self._send_chunk(data, current_segment)
            current_segment += 1

        logger.info('end segments: %s, %s', current_segment, final_segment)
        self.con.emit_signal(sender, object_path,
                             interface_name, 'complete',
                             GLib.Variant('(si)', (name, current_segment)))

    def sendFinish(self, data):
        # we don't need to do anything here because we write the file in
        # setContent, we don't do it here because that would require us to
        # cache big chunks of data in memory.
        pass

if __name__ == '__main__':
    import re
    from .tests import utils

    parser = utils.process_args()
    parser.add_argument("-c", "--cost", default=10)
    parser.add_argument("-o", "--output")
    parser.add_argument("url")
    args = parser.parse_args()

    if args.name:
        name = args.name
    else:
        name = re.sub('https?://', '', args.url)

    consumer = Consumer(name=name, url=args.url)
    utils.run_consumer_test(consumer, name, args)
