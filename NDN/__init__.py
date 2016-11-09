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

class Base(GObject.GObject):
    __gsignals__ = {
        'face-process-event': (GObject.SIGNAL_RUN_FIRST, None,
                    (object,)),
    }

    def __init__(self, name, face=None):
        GObject.GObject.__init__(self)
        self.name = name

        # The default Face will connect using a Unix socket, or to "localhost".
        if type(face) == Face:
            self.face = face
        else:
            try:
                self.face = Face(face)
            except:
                self.face = Face()

        self._callbackCount = 0
        self._responseCount = 0

        GLib.timeout_add(200, self.processEvents)

    def processEvents(self):
        self.face.processEvents()
        self.emit('face-process-event', self.face)
        return True

class Producer(Base):
    __gsignals__ = {
        'register-failed': (GObject.SIGNAL_RUN_FIRST, None,
                    (object,)),
        'register-success': (GObject.SIGNAL_RUN_FIRST, None,
                    (object, object)),
        'interest': (GObject.SIGNAL_RUN_FIRST, None,
                     (object, object, object, object, object))
    }

    def __init__(self, *args, **kwargs):
        super(Producer, self).__init__(*args, **kwargs)

        self.generateKeys()
        self.prefixes = dict()

        if (self.onInterest):
            print 'auto-connecting onInterest Signal'
            self.connect('interest', self.onInterest)

    def generateKeys(self):
        # Use the system default key chain and certificate name to sign commands.
        keyChain = KeyChain()
        self._keyChain = keyChain
        try:
            self._certificateName = keyChain.getDefaultCertificateName()
        except:
            name = Name (self.name)
            print "warning could not get default certificate name, creating a new one from %s" % name.toUri()
            self._certificateName = keyChain.createIdentityAndCertificate(name)
        self._responseCount = 0

        self.face.setCommandSigningInfo(keyChain, self._certificateName)

    def sign(self, data):
        return self._keyChain.sign(data, self._certificateName)

    def send(self, name, content):
        data = Data(name)
        data.setContent(content)
        self.sign(data)

        print("Sent Segment", seg)
        face.putData(data)

    def _onInterest(self, *args, **kwargs):
        self._responseCount += 1
        print ("Got interest", interest.toUri())

        self.emit('interest', *args, **kwargs)
        return self.onInterest(*args, **kwargs)

    def removeRegisteredPrefix(self, prefix):
        name = Name(prefix)
        print "Un-Register prefix", name.toUri()
        try:
            self.face.removeRegisteredPrefix(self.prefixes[name])
            del (self.prefixes[name])
        except:
            print "tried to unregister a prefix that never was registred: ", prefix
            pass

    def registerPrefix(self, prefix = None,
                       postfix = "", flags = None):
        if type(prefix) is str:
            prefix = Name(prefix)

        if not prefix:
            prefix = Name(path.join(self.name, postfix))

        if not flags:
            flags = self.flags

        print "Register prefix", prefix.toUri()
        self.prefixes[prefix] = self.face.registerPrefix(prefix,
                                  self._onInterest,
                                  self.onRegisterFailed,
                                  self.onRegisterSuccess,
                                  flags=flags)
        print 'prefixes', self.prefixes
        return prefix

    def onRegisterFailed(self, prefix):
        self._responseCount += 1
        self.emit('register-failed', prefix)
        print("Register failed for prefix", prefix.toUri())

    def onRegisterSuccess(self, prefix, registered):
        self.emit('register-success', prefix, registered)
        print("Register succeded for prefix", prefix.toUri(), registered)

class Consumer(Base):
    __gsignals__ = {
        'data': (GObject.SIGNAL_RUN_FIRST, None,
                 (object, object)),
        'interest-timeout': (GObject.SIGNAL_RUN_FIRST, None,
                 (object,)),
    }

    def __init__(self, *args, **kwargs):
        super(Consumer, self).__init__(*args, **kwargs)

        self.pit = dict()
#        self.generateKeys()
        self.prefixes = dict()

        if (self.onData):
            print 'auto-connecting onData Signal'
            self.connect('data', self.onData)

    def _onData(self, *args, **kwargs):
        self._callbackCount += 1
        self.emit('data', *args, **kwargs)

    def expressInterest(self, name=None, forever=False):
        if name == None: name = self.name
        segname = Name(name).appendSegment(0)
        print "Express Interest name:", segname.toUri()
        onTimeout = partial(self.onTimeout, forever=forever, name=name)
        self.pit[name] = self.face.expressInterest(segname, self._onData, onTimeout)

    def removePendingInterest(self, name):
        self.face.removePendingInterest(self.pit[name])
        del self.pit[name]

    def onTimeout(self, interest, forever=False, name=None):
        self._callbackCount += 1
        self.emit('interest-timeout', interest)
        print "Time out for interest", interest.getName().toUri()
        if forever and name:
            print "Re-requesting Interest", name
            onTimeout = partial(self.onTimeout, forever=forever, name=name)
            self.pit[name] = self.face.expressInterest(interest.getName(),
                                                       self._onData, onTimeout)
