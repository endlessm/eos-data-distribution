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

import Chunks
import NDN

from gi.repository import GLib

def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename")
    parser.add_argument("-l", "--limit", default=3)
    parser.add_argument("-n", "--no-chunks", action='store_true')
    parser.add_argument("name")

    args = parser.parse_args()
    if not args.filename:
        args.filename = args.name.split('/')[-1]

    face = Face()

    if args.no_chunks:
        consumer = NDN.Consumer(args.name, face=face, auto=True)
    else:
        args.name += "/chunked/"
        consumer = Chunks.Consumer(args.name, args.filename, face=face, auto=True)

    loop = GLib.MainLoop()

    def check(o, f):
        if args.limit and consumer._callbackCount > args.limit:
            loop.quit()

    consumer.connect('face-process-event', check)
    loop.run()
