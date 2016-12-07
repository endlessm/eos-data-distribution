#!/usr/bin/python
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

import json
import logging
from functools import partial
from os import path

from pyndn import Name
from pyndn import Data

from .. import NDN, Chunks, HTTP
from ..NDN import Endless

import gi
gi.require_version('Soup', '2.4')

from gi.repository import GLib
from gi.repository import Soup

logger = logging.getLogger(__name__)


def getSubIdName(name, basename):
    return name.getSubName(basename.size()).get(0)


class Getter(NDN.Producer):
    def __init__(self, name, *args, **kwargs):
        super(Getter, self).__init__(name=name, *args, **kwargs)

        self.getters = dict()

        self.connect('interest', self.onInterest)

    def onInterest(self, o, prefix, interest, face, interestFilterId, filter):
        name = interest.getName()
        chunked = str(name.get(-1))
        if not chunked == 'chunked':
            logger.debug('ignoring non-chunked request: %s', name)
            return False

        name = name.getPrefix(-1)

        filename = str(name.get(-1))
        filepath = name.getSubName(Endless.NAMES.SOMA.size())
        key = str(name)

        try:
            getter = self.getters[key]
        except:
            if filename.endswith('.json'):
                getter = self.getters[key] = HTTP.Producer(name, "%s%s" % (Endless.SOMA_SUB_BASE, filepath), face=face, auto=True)
            elif filename.endswith('.shard'):
                url = "http://" + str(filepath).replace('/shards/', '')
                getter = self.getters[key] = HTTP.Producer(name, url, face=face, auto=True)
            else:
                logger.debug('ignoring request: %s → %s', filename, name)
                return False

        return getter


if __name__ == '__main__':
    from gi.repository import GLib
    import time

    EG = Getter(NDN.Endless.NAMES.SOMA)
    name = Name(NDN.Endless.NAMES.SOMA).append('10521bb3a18b573f088f84e59c9bbb6c2e2a1a67')
    print Chunks.Consumer(name, filename='test.json', auto=True)

    GLib.MainLoop().run()
