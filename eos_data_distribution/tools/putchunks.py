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

import argparse
import sys
import time

from pyndn import Name

from gi.repository import GLib

from eos_data_distribution.ndn.file import FileProducer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("filename")
    args = parser.parse_args()

    f = open(args.filename, 'rb')
    producer = FileProducer(args.name, f, auto=True)
    loop = GLib.MainLoop()
    loop.run()