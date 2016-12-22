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
from os import path
from functools import partial

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GObject
from gi.repository import GLib

from pyndn.node import Node
from pyndn.security import KeyChain
from pyndn.transport.unix_transport import UnixTransport
from pyndn import Name, Data, Face, MetaInfo

logger = logging.getLogger(__name__)


def makeName(o):
    if isinstance(o, Name):
        return o
    return Name(o)


class GLibUnixTransport(UnixTransport):
    _watch_id = 0

    def connect(self, connectionInfo, elementListener, onConnected):
        super(GLibUnixTransport, self).connect(connectionInfo, elementListener, onConnected)

        fd = self._socket.fileno()
        io_channel = GLib.IOChannel.unix_new(fd)
        self._watch_id = GLib.io_add_watch(io_channel, GLib.PRIORITY_DEFAULT, GLib.IO_IN, self._socket_ready)

    def _socket_ready(self, channel, cond):
        nBytesRead = self._socket.recv_into(self._buffer)
        if nBytesRead <= 0:
            # Since we checked for data ready, we don't expect this.
            return

        self._elementReader.onReceivedData(self._bufferView[0:nBytesRead])
        return GLib.SOURCE_CONTINUE

    def close(self):
        super(GLibUnixTransport, self).close()

        if self._watch_id != 0:
            GLib.source_remove(self._watch_id)
            self._watch_id = 0


class GLibUnixFace(Face):
    def __init__(self):
        transport = GLibUnixTransport()
        file_path = self._getUnixSocketFilePathForLocalhost()
        connection_info = UnixTransport.ConnectionInfo(file_path)

        self._node = Node(transport, connection_info)
        self._commandKeyChain = None
        self._commandCertificateName = Name()

    def callLater(self, delayMilliseconds, callback):
        # Wrapper to ensure we remove the source.
        def wrap():
            callback()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(delayMilliseconds, wrap)


def singleton(f):
    instance = [None]
    def inner():
        if instance[0] is None:
            instance[0] = f()
        return instance[0]
    return inner


@singleton
def get_default_face():
    return GLibUnixFace()


class Base(GObject.GObject):
    def __init__(self, name, face=None):
        GObject.GObject.__init__(self)
        self.name = Name(name)

        if face is not None:
            assert isinstance(face, GLibUnixFace)
            self.face = face
        else:
            self.face = get_default_face()

        self._callbackCount = 0


class Consumer(Base):
    __gsignals__ = {
        'data': (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        'interest-timeout': (GObject.SIGNAL_RUN_FIRST, None, (object, )),
    }

    def __init__(self, name=None, *args, **kwargs):
        super(Consumer, self).__init__(name=name, *args, **kwargs)

        self.pit = dict()
        #        self.generateKeys()
        self._prefixes = dict()

    def consume(self):
        self.expressInterest()

    def _onData(self, interest, data):
        self._callbackCount += 1
        # that is complicated… getContent() returns an ndn.Blob, that needs
        # to call into buf() to get a bytearray…
        self.emit('data', interest, data)

    def expressInterest(self, name=None, forever=False):
        if name is None:
            name = self.name

        logger.debug("Express Interest name: %s", name)
        onTimeout = partial(self.onTimeout, forever=forever, name=name)
        self.pit[name] = self.face.expressInterest(name, self._onData, onTimeout)

    def removePendingInterest(self, name):
        self.face.removePendingInterest(self.pit[name])
        del self.pit[name]

    def onTimeout(self, interest, forever=False, name=None):
        self._callbackCount += 1
        self.emit('interest-timeout', interest)
        logger.debug("Time out for interest: %s", interest.getName())
        if forever and name:
            logger.info("Re-requesting Interest: %s", name)
            onTimeout = partial(self.onTimeout, forever=forever, name=name)
            self.pit[name] = self.face.expressInterest(interest, self._onData, onTimeout)
