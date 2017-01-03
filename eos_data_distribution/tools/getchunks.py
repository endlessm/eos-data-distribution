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
import logging
import sys
import time

from pyndn import Name

from gi.repository import GLib

from eos_data_distribution.ndn.file import FileConsumer
from eos_data_distribution.tools import util


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("filename")
    parser.add_argument("-l", "--limit", type=int, default=0)

    args = util.process_args(parser)

    consumer = FileConsumer(args.name, args.filename, auto=True)

    def check(consumer, pct):
        if args.limit and consumer._callbackCount > args.limit:
            complete()

    consumer.connect('progress', check)

    def complete(*a):
        loop.quit()

    consumer.connect('complete', complete)
    loop = GLib.MainLoop()
    loop.run()

if __name__ == '__main__':
    main()
