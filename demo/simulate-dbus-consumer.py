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

import logging
import json
from os import path

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GObject
from gi.repository import GLib

from eos_data_distribution.ndn.dbus.base import Consumer, Interest
from eos_data_distribution.names import Name, SUBSCRIPTIONS_INSTALLED

logger = logging.getLogger(__name__)

class DbusConsumer(Consumer):

    def __init__(self, name, target, appids, v=None, *args, **kwargs):
        Consumer.__init__(self, name=name, *args, **kwargs)

        self.target = target
        self.connect('data', self.notifyEKN)

        appname = lambda i: Interest(Name(SUBSCRIPTIONS_INSTALLED).append(i))
        [self.expressInterest(appname(i), try_again=True) for i in appids]

    def notifyEKN(self, consumer, interest, data):
        logger.info("GOT NAMES, all the names, the best names")


if __name__ == "__main__":
    import sys
    import argparse
    from eos_data_distribution import utils

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", default='./tmp')
    parser.add_argument("-n", "--name", default=SUBSCRIPTIONS_INSTALLED)
    parser.add_argument("appids", nargs='+')

    args = utils.parse_args(parser=parser, include_name=False)
    kwargs = args.__dict__

    print('spawning DbusConsumer', kwargs)

    consumer = DbusConsumer(**kwargs)

    GLib.MainLoop().run()
