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

import gi
gi.require_version('Soup', '2.4')

from gi.repository import GLib
from gi.repository import Soup

from ..ndn import Endless
from .. import ndn

logger = logging.getLogger(__name__)


def getSubIdName(name, basename):
    return name.getSubName(basename.size()).get(0)


class Fetcher(object):
    def __init__(self):
        self._producer = Producer(Endless.NAMES.SOMA)
        self._producer.connect('interest', self._on_interest)
        self._producer.registerPrefix()

        self._subproducers = {}

    def _on_interest(self, o, prefix, interest, face, interestFilterId, filter):
        name = interest.getName()
        key = str(name)

        # If we already have a producer for this name, then we're good...
        if key in self._subproducers:
            return

        filename = str(name.get(-1))
        filepath = name.getSubName(Endless.NAMES.SOMA.size())

        # Else, we need to create a
        if filename.endswith('.json'):
            self._subproducers[key] = http.Producer(name, "%s%s" % (Endless.SOMA_SUB_BASE, filepath), face=face, auto=True)
        elif filename.endswith('.shard'):
            url = "http://" + str(filepath).replace('/shards/', '')
            self._subproducers[key] = http.Producer(name, url, face=face, auto=True)
        else:
            logger.debug('ignoring request: %s → %s', filename, name)
