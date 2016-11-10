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

from pyndn import Name
from pyndn import Face

import Chunks
import NDN

import json

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GObject
from gi.repository import GLib

from os import path

def dump(*list, **kwargs):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

class DbusConsumer(NDN.Consumer):
    def __init__(self, name, target, *args, **kwargs):
        NDN.Consumer.__init__(self, name, *args, **kwargs)

        self.target = target
        self.expressInterest(forever=True)
        self.connect('data', self.getShards)

    def getShards(self, consumer, interest, data):
        buf = self.dataToBytes(data)
        names = json.loads(str(buf))
        self.chunks = [Chunks.Consumer(n, path.join(self.target, path.basename(n))) for n in names]
        [c.expressInterest() for c in self.chunks]

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", default='./tmp')
    parser.add_argument("name")

    args = parser.parse_args()
    kwargs = args.__dict__

    consumer = DbusConsumer(**kwargs)

    GLib.MainLoop().run()
