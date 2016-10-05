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

from pyndn.security import KeyChain

from pyndn import Name
from pyndn import Data
from pyndn import Face

from os import path

class Chunks(object):
    def __init__(self, name, filename=None, chunkSize = 4096, mode="r+", face=None):
        self.name = name
        self.filename = filename

        if filename:
            self.f = open(filename, mode)

        self.chunkSize = chunkSize

        # The default Face will connect using a Unix socket, or to "localhost".
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
        print("Register failed for prefix", prefix.toUri())

    def onRegisterSuccess(self, prefix, registered):
        print("Register succeded for prefix", prefix.toUri(), registered)

    def onTimeout(self, interest):
        self._callbackCount += 1
        print("Time out for interest", interest.getName().toUri())

class Producer(Chunks):
    def __init__(self, name, filename=None, chunkSize = 4096, face=None):
        super(Producer, self).__init__(name, filename, chunkSize,
                                       mode="r+", face=face)
        self.generateKeys()

    def generateKeys(self):
        # Use the system default key chain and certificate name to sign commands.
        keyChain = KeyChain()
        self._keyChain = keyChain
        self._certificateName = keyChain.getDefaultCertificateName()
        self._responseCount = 0

        self.face.setCommandSigningInfo(keyChain, self._certificateName)

    def getChunk(self, n):
        self.f.seek(self.chunkSize * n)
        return self.f.read(self.chunkSize)

    def onInterest(self, prefix, interest, face, interestFilterId, filter):
        self._responseCount += 1

        print ("Got interest", interest.toUri())

        # Make and sign a Data packet.
        name = interest.getName()
        data = Data(name)
        # hack to get the segment number
        seg = int(repr(name).split('%')[-1])

        content = "%s;" % self.chunkSize
        content += self.getChunk(seg)
        data.setContent(content)
        self._keyChain.sign(data, self._certificateName)

        print("Sent Segment", seg)
        face.putData(data)

    def registerPrefix(self, prefix = None,
                       postfix = "", flags = None):
        if not prefix:
            prefix = Name(path.join(self.name, postfix))
        print("Register prefix", prefix.toUri(), "chunkSize", self.chunkSize)
        self.face.registerPrefix(prefix, self.onInterest,
                                 self.onRegisterFailed,
                                 self.onRegisterSuccess,
                                 flags=flags)
        return prefix

class Consumer(Chunks):
    def __init__(self, name, filename, chunkSize = 4096, face=None):
        super(Consumer, self).__init__(name, filename, chunkSize,
                                       mode="w+", face=face)

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
        seg = int(repr(name).split('%')[-1])

        print("Got data packet with name", name.toUri())
        self.putChunk(seg, data.getContent())
        name = Name(interest.name).getSuccessor()
        self.face.expressInterest(name, self.onData, self.onTimeout)

    def expressInterest(self):
        name = Name(self.name).appendSegment(0)
        print("Express name:", name.toUri())
        self.face.expressInterest(name, self.onData, self.onTimeout)

