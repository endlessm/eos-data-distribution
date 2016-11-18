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

from pyndn.security import KeyChain

from pyndn import Name
from pyndn import Data
from pyndn import Face

from os import path
from functools import partial

from NDN import Endless

import logging
logging.basicConfig(level=Endless.LOGLEVEL)
logger = logging.getLogger(__name__)

def makeName(o):
    if isinstance(o, Name):
        return o
    return Name(o)

def dumpName(n):
    return [str (n.get(i)) for i in range(n.size())]

class Base(GObject.GObject):
    __gsignals__ = {
        'face-process-event': (GObject.SIGNAL_RUN_FIRST, None,
                    (object,)),
    }

    def __init__(self, name, face=None, tick=100):
        GObject.GObject.__init__(self)
        self.name = Name(name)
        self.tick = tick

        # The default Face will connect using a Unix socket, or to "localhost".
        if type(face) == Face:
            self.face = face
            logger.info('re-using face: %s', face)
        else:
            logger.info('creating a new face')
            try:
                self.face = Face(face)
            except:
                self.face = Face()
            GLib.timeout_add (tick, self.processEvents)

        self._callbackCount = 0
        self._responseCount = 0

    def processEvents(self):
        self.face.processEvents()
        self.emit('face-process-event', self.face)
        return True

    def dataToBytes(self, data):
        return bytearray(data.getContent().buf())

class Producer(Base):
    __gsignals__ = {
        'register-failed': (GObject.SIGNAL_RUN_FIRST, None,
                    (object,)),
        'register-success': (GObject.SIGNAL_RUN_FIRST, None,
                    (object, object)),
        'interest': (GObject.SIGNAL_RUN_FIRST, None,
                     (object, object, object, object, object))
    }

    def __init__(self, auto=False, *args, **kwargs):
        super(Producer, self).__init__(*args, **kwargs)

        self.generateKeys()
        self._prefixes = dict()

        if auto: self.produce()

    def produce(self):
        self.registerPrefix()

    def generateKeys(self):
        # Use the system default key chain and certificate name to sign commands.
        keyChain = KeyChain()
        self._keyChain = keyChain
        try:
            self._certificateName = keyChain.getDefaultCertificateName()
        except:
            name = Name (self.name)
            logger.warning("Could not get default certificate name, creating a new one from %s", dumpName(name))
            self._certificateName = keyChain.createIdentityAndCertificate(name)
        self._responseCount = 0

        self.face.setCommandSigningInfo(keyChain, self._certificateName)

    def sign(self, data):
        return self._keyChain.sign(data, self._certificateName)

    def send(self, name, content):
        data = Data(name)
        data.setContent(content)
        logger.debug ('sending: %d, on %s', content.__len__(), dumpName(name))
        self.sendFinish(data)
        return name

    def sendFinish(self, data):
        self.sign(data)
#       logger.debug ('sending data: %d', data.__len__())
        self.face.putData(data)

    def _onInterest(self, *args, **kwargs):
        self._responseCount += 1
        logger.info ("Got interest %s, %s", args, kwargs)

        self.emit('interest', *args, **kwargs)

    def removeRegisteredPrefix(self, prefix):
        name = Name(prefix)
        logger.info("Un-Register prefix: %s", dumpName(name))
        try:
            self.face.removeRegisteredPrefix(self._prefixes[name])
            del (self._prefixes[name])
        except:
            logger.warning("tried to unregister a prefix that never was registred: %s", prefix)
            pass

    def registerPrefix(self, prefix = None,
                       postfix = "", flags = None):
        prefix = makeName(prefix)
        postfix = makeName(postfix)

        if not prefix:
            prefix = Name(self.name).append(postfix)
        try:
            flags = flags or self.flags
        except:
            flags = None

        logger.info ("Register prefix: %s", dumpName(prefix))
        self._prefixes[prefix] = self.face.registerPrefix(prefix,
                                  self._onInterest,
                                  self.onRegisterFailed,
                                  self.onRegisterSuccess,
                                  flags=flags)
        return prefix

    def onRegisterFailed(self, prefix):
        self._responseCount += 1
        self.emit('register-failed', prefix)
        logger.warning("Register failed for prefix: %s", dumpName(prefix))

    def onRegisterSuccess(self, prefix, registered):
        self.emit('register-success', prefix, registered)
        logger.info("Register succeded for prefix: %s, %s", dumpName(prefix), registered)

class Consumer(Base):
    __gsignals__ = {
        'data': (GObject.SIGNAL_RUN_FIRST, None,
                 (object, object)),
        'interest-timeout': (GObject.SIGNAL_RUN_FIRST, None,
                 (object,)),
    }

    def __init__(self, auto=False, *args, **kwargs):
        super(Consumer, self).__init__(*args, **kwargs)

        self.pit = dict()
#        self.generateKeys()
        self._prefixes = dict()
        if auto: self.consume()

    def consume(self):
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
        if postfix: segname.append (postfix)
        logger.info ("Express Interest name: %s", dumpName(segname))
        onTimeout = partial(self.onTimeout, forever=forever, name=name)
        self.pit[name] = self.face.expressInterest(segname, self._onData, onTimeout)

    def removePendingInterest(self, name):
        self.face.removePendingInterest(self.pit[name])
        del self.pit[name]

    def onTimeout(self, interest, forever=False, name=None):
        self._callbackCount += 1
        self.emit('interest-timeout', interest)
        logger.info ("Time out for interest: %s", dumpName(interest.getName()))
        if forever and name:
            logger.info ("Re-requesting Interest: %s", name)
            onTimeout = partial(self.onTimeout, forever=forever, name=name)
            self.pit[name] = self.face.expressInterest(interest.getName(),
                                                       self._onData, onTimeout)
