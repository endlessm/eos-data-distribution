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

from Chunks import Producer as Chunks

def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

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

    chunks = Chunks(name, filename, chunkSize)
    chunks.registerPrefix()

    while chunks._responseCount < 100:
        face.processEvents()
        # We need to sleep for a few milliseconds so we don't use 100% of the CPU.
        time.sleep(0.01)

    face.shutdown()
