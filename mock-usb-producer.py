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

from os import path

import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib

from eos_ndn.NDN import Endless
from eos_ndn.SimpleStore import Producer as SimpleStoreProducer

import logging
logging.basicConfig(level=Endless.LOGLEVEL)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("dir")
    args = parser.parse_args()

    store = SimpleStoreProducer(prefix=Endless.NAMES.SOMA, split=path.realpath(args.dir))
    logger.info('creating store: %s', args.__dict__)
    store.publish_all_names(path.realpath(args.dir))

    GLib.MainLoop().run()
