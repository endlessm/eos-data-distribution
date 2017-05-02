#!/usr/bin/python
# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2016 Endless Mobile, Inc.
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

import os
import json
import logging

from gi.repository import GLib

from .names import SUBSCRIPTIONS_SOMA
from .ndn import http, manifest
from .ndn.dbus import chunks
from .ndn.dbus.base import Producer

logger = logging.getLogger(__name__)


def getSubIdName(name, basename):
    return name.getSubName(basename.size()).get(0)


def get_cluster_type():
    return os.environ.get('SOMA_CLUSTER_TYPE', 'prod')


def get_soma_server():
    server = os.getenv('EKN_SUBSCRIPTIONS_FRONTEND')
    if server is not None:
        return server
    else:
        return 'https://subscriptions.%s.soma.endless-cloud.com' % (get_cluster_type(), )


class Fetcher(object):

    def __init__(self):
        self._producer = Producer(SUBSCRIPTIONS_SOMA)
        self._producer.connect('interest', self._on_interest)
        self._producer.registerPrefix()

        self._subproducers = {}

    def _on_interest(self, o, prefix, interest, face, interestFilterId, filter):
        # We handle one of two paths:
        #   /com.endlessm/subscriptions/soma/subscription/$sub_id/manifest.json/$chunk
        #   /com.endlessm/subscriptions/soma/shard/$shard_url/$chunk

        name = interest.getName()

        chunkless_name = chunks.get_chunkless_name(name)
        key = str(chunkless_name)

        # If we already have a producer for this name, then we're good...
        if key in self._subproducers:
            return

        # we can't have a component, we're getting bootstrapping interests
        if chunkless_name.size() <= SUBSCRIPTIONS_SOMA.size():
            return

        route = chunkless_name.getSubName(SUBSCRIPTIONS_SOMA.size())
        component = route.get(0).getValue().toRawStr()

        if component == 'subscription':
            subscription_id = route.get(1).getValue().toRawStr()
            filename = route.get(2).getValue().toRawStr()
            assert filename == 'manifest.json'
            self._subproducers[key] = http.Producer(
                chunkless_name, "%s/v1/%s/manifest.json" % (get_soma_server(), subscription_id), face=face)
            self._subproducers[key].start()
        elif component == 'shard':
            shard_url = route.get(1).getValue().toRawStr()
            self._subproducers[key] = http.Producer(
                chunkless_name, shard_url, face=face)
            self._subproducers[key].start()
        else:
            logger.warning('ignoring request: %s', name)
