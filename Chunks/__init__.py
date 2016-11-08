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

class Chunks(GObject.GObject):
    __gsignals__ = {
        'register-failed': (GObject.SIGNAL_RUN_FIRST, None,
                    (object,)),
        'register-success': (GObject.SIGNAL_RUN_FIRST, None,
                    (object, object)),
        'interest-timeout': (GObject.SIGNAL_RUN_FIRST, None,
                    (object,)),
        'face-process-event': (GObject.SIGNAL_RUN_FIRST, None,
                    (object,)),

    }

    def __init__(self, name, filename=None, chunkSize = 4096, mode="r+",
                 face=None):
        GObject.GObject.__init__(self)
        self.name = name
        self.filename = filename

        if filename:
            self.f = open(filename, mode)

        self.chunkSize = chunkSize

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

    def processEvents(self):
        self.face.processEvents()
        return True

    def onRegisterFailed(self, prefix):
        self._responseCount += 1
        self.emit('register-failed', prefix)
        print("Register failed for prefix", prefix.toUri())

    def onRegisterSuccess(self, prefix, registered):
        self.emit('register-success', prefix, registered)
        print("Register succeded for prefix", prefix.toUri(), registered)

    def onTimeout(self, interest):
        self._callbackCount += 1
        self.emit('interest-timeout', interest)
        print("Time out for interest", interest.getName().toUri())

class Producer(Chunks):
    def __init__(self, name, filename=None, chunkSize=4096, face=None):
        super(Producer, self).__init__(name, filename, chunkSize,
                                       mode="r+", face=face)
        self.generateKeys()
        self.prefixes = dict()

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

    def getChunk(self, name, n, prefix=None):
        self.f.seek(self.chunkSize * n)
        return self.f.read(self.chunkSize)

    def _onInterest(self, *args, **kwargs):
        self._responseCount += 1
        print ("Got interest", interest.toUri())

        return self.onInterest(*args, **kwargs)

    def onInterest(self, prefix, interest, face, interestFilterId, filter):
        # Make and sign a Data packet.
        name = interest.getName()
        data = Data(name)
        # hack to get the segment number
        seg = int(repr(name).split('%')[-1], 16)

        content = "%s;" % self.chunkSize
        content += self.getChunk(name, seg, prefix=prefix)
        data.setContent(content)
        self._keyChain.sign(data, self._certificateName)

        print("Sent Segment", seg)
        face.putData(data)

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
        if not prefix:
            prefix = Name(path.join(self.name, postfix))
        print "Register prefix", prefix.toUri()
        self.prefixes[prefix] = self.face.registerPrefix(prefix,
                                  self._onInterest,
                                  self.onRegisterFailed,
                                  self.onRegisterSuccess,
                                  flags=flags)

        return prefix

class Consumer(Chunks):
    def __init__(self, name, filename, chunkSize = 4096, face=None):
        super(Consumer, self).__init__(name, filename, chunkSize,
                                       mode="w+", face=face)
        self.pit = dict()

    def putChunk(self, n, data):
        buf = data.buf()
        chunkSize = str(bytearray(buf[:10])).split(';')[0]
        skip = len(chunkSize) + 1
        chunkSize = int(chunkSize)
        print ("got data, seq: %d, chunksize: %d, skip: %d" % (n, chunkSize, skip))
        self.f.seek(chunkSize * n)
        # that was complicated… getContent() returns an ndn.Blob, that needs
        # to call into buf() to get a bytearray…
        return self.f.write(bytearray(buf)[skip:])

    def onData(self, interest, data):
        self._callbackCount += 1
        name = data.getName()
        seg = int(repr(name).split('%')[-1], 16)

        print("Got data packet with name", name.toUri())
        self.putChunk(seg, data.getContent())
        name = Name(interest.name).getSuccessor()
        self.face.expressInterest(name, self.onData, self.onTimeout)

    def expressInterest(self, name=None):
        if not name: name = self.name
        segname = Name(name).appendSegment(0)
        print("Express name:", segname.toUri())
        self.pit[name] = self.face.expressInterest(segname, self.onData, self.onTimeout)

    def removePendingInterest(self, name):
        self.face.removePendingInterest(self.pit[name])
        del self.pit[name]

