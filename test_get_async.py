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
from pyndn import Face

def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

class Chunks(object):
    def __init__(self, face, filename, chunkSize = 4096):
        self.filename = filename
        self.f = open(filename, "w+")

        self.chunkSize = chunkSize
        self._callbackCount = 0
        self.face = face


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

        dump("Got data packet with name", name.toUri())
        # Use join to convert each byte to chr.
        self.putChunk(seg, data.getContent())
        name = Name(interest.name).getSuccessor()
        self.face.expressInterest(name, self.onData, self.onTimeout)

    def onTimeout(self, interest):
        self._callbackCount += 1
        dump("Time out for interest", interest.getName().toUri())

if __name__ == "__main__":
    import sys
    arg = 1

    filename = sys.argv[1]

    try:
        name = sys.argv[2]
    except:
        name = "/endless/testchunks"

    name += "/chunked/"

    face = Face()
    chunks = Chunks(face, filename)

    # Try to fetch.
    name1 = Name(name).appendSegment(0)
    dump("Express name:", name1.toUri())
    face.expressInterest(name1, chunks.onData, chunks.onTimeout)

    while chunks._callbackCount < 3:
        face.processEvents()
        # We need to sleep for a few milliseconds so we don't use 100% of the CPU.
        time.sleep(0.01)

    face.shutdown()
