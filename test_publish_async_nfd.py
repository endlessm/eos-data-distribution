# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2014-2016 Regents of the University of California.
# Author: Jeff Thompson <jefft0@remap.ucla.edu>
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

import time
from pyndn import Name
from pyndn import Data
from pyndn import Face
from pyndn.security import KeyChain

def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

class Chunks(object):
    def __init__(self, filename, face, chunkSize = 4096):
        self.filename = filename
        self.f = open(filename)
        self.face = face
        self.chunkSize = chunkSize

        # Use the system default key chain and certificate name to sign commands.
        keyChain = KeyChain()
        self._keyChain = keyChain
        self._certificateName = keyChain.getDefaultCertificateName()
        self._responseCount = 0

        face.setCommandSigningInfo(keyChain, self._certificateName)

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

        dump("Sent Segment", seg)
        face.putData(data)

    def onRegisterFailed(self, prefix):
        self._responseCount += 1
        dump("Register failed for prefix", prefix.toUri())

if __name__ == "__main__":
    import sys

    filename = sys.argv[1]

    try:
        name = sys.argv[2]
    except:
        name = "/endless/testchunks/" + filename

    try:
        chunkSize = sys.argv[3]
    except:
        chunkSize = 4096

    print (sys.argv)

    # The default Face will connect using a Unix socket, or to "localhost".
    face = Face()

    # Also use the default certificate name to sign data packets.
    chunks = Chunks(filename, face, chunkSize)

    name += "/chunked"
    prefix = Name(name)
    dump("Register prefix", prefix.toUri(), "chunkSize", chunkSize)
    face.registerPrefix(prefix, chunks.onInterest, chunks.onRegisterFailed)

    while chunks._responseCount < 100:
        face.processEvents()
        # We need to sleep for a few milliseconds so we don't use 100% of the CPU.
        time.sleep(0.01)

    face.shutdown()
