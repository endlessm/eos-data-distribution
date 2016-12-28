# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2016 Endless Mobile, Inc.
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
        self._responseCount = 0


class Producer(Base):
    __gsignals__ = {
        'register-failed': (GObject.SIGNAL_RUN_FIRST, None, (object, )),
        'register-success': (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        'interest': (GObject.SIGNAL_RUN_FIRST, None, (object, object, object, object, object))
    }

    def __init__(self, name=None, auto=False, *args, **kwargs):
        super(Producer, self).__init__(name=name, *args, **kwargs)

        self.generateKeys()
        self._prefixes = dict()

        if auto: self.start()

    def start(self):
        self.registerPrefix()

    def generateKeys(self):
        # Use the system default key chain and certificate name to sign commands.
        self._key_chain = KeyChain()
        self._cert_name = self._key_chain.getDefaultCertificateName()
        self.face.setCommandSigningInfo(self._key_chain, self._cert_name)

    def sign(self, data):
        return self._key_chain.sign(data, self._cert_name)

    def send(self, name, content):
        data = Data(name)
        data.setContent(content)
        logger.debug('sending: %d, on %s', content.__len__(), name)
        self.sendFinish(data)
        return name

    def sendFinish(self, data):
        # self.sign(data)
        # logger.debug ('sending data: %d', data.__len__())
        self.face.putData(data)

    def _onInterest(self, *args, **kwargs):
        self._responseCount += 1
        logger.debug("Got interest %s, %s", args, kwargs)

        self.emit('interest', *args, **kwargs)

    def removeRegisteredPrefix(self, prefix):
        name = Name(prefix)
        logger.info("Un-Register prefix: %s", name)
        try:
            self.face.removeRegisteredPrefix(self._prefixes[name])
            del (self._prefixes[name])
        except:
            logger.warning("tried to unregister a prefix that never was registred: %s", prefix)
            pass

    def registerPrefix(self, prefix=None, postfix="", flags=None):
        prefix = makeName(prefix)
        postfix = makeName(postfix)

        if not prefix:
            prefix = Name(self.name).append(postfix)
        try:
            flags = flags or self.flags
        except:
            flags = None

        logger.info("Register prefix: %s", prefix)
        self._prefixes[prefix] = self.face.registerPrefix(prefix, self._onInterest, self.onRegisterFailed, self.onRegisterSuccess, flags=flags)
        return prefix

    def onRegisterFailed(self, prefix):
        self._responseCount += 1
        self.emit('register-failed', prefix)
        logger.warning("Register failed for prefix: %s", prefix)

    def onRegisterSuccess(self, prefix, registered):
        self.emit('register-success', prefix, registered)
        logger.info("Register succeded for prefix: %s, %s", prefix, registered)


class Consumer(Base):
    __gsignals__ = {
        'data': (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        'interest-timeout': (GObject.SIGNAL_RUN_FIRST, None, (object, )),
    }

    def __init__(self, name=None, auto=False, *args, **kwargs):
        super(Consumer, self).__init__(name=name, *args, **kwargs)

        self.pit = dict()
        #        self.generateKeys()
        self._prefixes = dict()

        if auto: self.start()

    def start(self):
        self.expressInterest()

    def _onData(self, interest, data):
        self._callbackCount += 1
        # that is complicated… getContent() returns an ndn.Blob, that needs
        # to call into buf() to get a bytearray…
        self.emit('data', interest, data)

    def makeInterest(self, name):
        return Name(name)

    def expressInterest(self, name=None, forever=False, postfix=None):
        if name == None: name = self.name
        segname = self.makeInterest(name)
        if postfix: segname.append(postfix)
        logger.debug("Express Interest name: %s", segname)
        onTimeout = partial(self.onTimeout, forever=forever, name=name)
        self.pit[name] = self.face.expressInterest(segname, self._onData, onTimeout)
        return segname

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
