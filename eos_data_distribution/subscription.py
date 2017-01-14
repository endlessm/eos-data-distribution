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

import logging
import json
import os
from os import path

from pyndn import Name, Data

import gi
from gi.repository import GObject

from . import defaults, ndn
from .names import SUBSCRIPTIONS_SOMA, SUBSCRIPTIONS_INSTALLED
from .ndn.file import FileConsumer
from .soma_subscription_fetcher import getSubIdName
from .parallel import Batch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Fetcher(GObject.GObject):
    __gsignals__ = {
        'response': (GObject.SIGNAL_RUN_FIRST, None, (str, )),
        'complete': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, store_dir, subscription_id, face=None):
        super(Fetcher, self).__init__()

        self.subscription_id = subscription_id

        self._face = face
        self._store_dir = store_dir

        self._manifest_suffix = 'subscription/%s/manifest.json' % (self.subscription_id)
        self._manifest_filename = path.join(self._store_dir, self._manifest_suffix)
        self._shard_filenames = []

    def start(self):
        self._fetch_manifest()
        return self

    def _fetch_manifest(self):
        manifest_ndn_name = Name('%s/%s' % (SUBSCRIPTIONS_SOMA, self._manifest_suffix))
        manifest_consumer = FileConsumer(manifest_ndn_name, self._manifest_filename, auto=True)
        manifest_consumer.connect('complete', self._fetch_manifest_complete)

    def _fetch_manifest_complete(self, consumer):
        with open(self._manifest_filename, 'r') as f:
            manifest = json.load(f)

        consumers = []
        for shard in manifest['shards']:
            shard_suffix = 'shard/%s' % (shard['download_uri'], )
            shard_ndn_name = Name('%s/%s' % (SUBSCRIPTIONS_SOMA, shard_suffix))
            shard_filename = path.realpath(path.join(self._store_dir, shard_suffix))
            self._shard_filenames.append(shard_filename)
            consumer = FileConsumer(shard_ndn_name, shard_filename, face=self._face)
            consumers.append(consumer)
            logger.info("Starting consumer: %s", (consumer, ))

        parallel_consumer = Batch(consumers, 'Consumers')
        parallel_consumer.connect('complete', self._on_shards_complete)

    def _on_shards_complete(self, parallel_consumer):
        response = {
            "subscription_id": self.subscription_id,
            "manifest_path": self._manifest_filename,
            "shards": self._shard_filenames,
        }

        self.emit('response', json.dumps(response))
        self.emit('complete')

# The Producer listens for intents to /endless/installed/foo,
# downloads the manifest and shards by fetching from /endless/soma/v1/foo/...,
# and then generates a "signalling response" for them.
class Producer(object):
    def __init__(self, store_dir):
        self._store_dir = store_dir
        self._fetchers = {}

        self._producer = ndn.Producer(SUBSCRIPTIONS_INSTALLED)
        self._producer.connect('interest', self._on_interest)

    def start(self):
        self._producer.registerPrefix()

    def _on_interest(self, o, prefix, interest, face, interestFilterId, filter):
        name = interest.getName()
        subscription_id = str(getSubIdName(name, SUBSCRIPTIONS_INSTALLED))

        if subscription_id in self._fetchers:
            return

        fetcher = Fetcher(self._store_dir, subscription_id, face=face)
        fetcher.connect('response', lambda fetcher, response: self._on_subscription_response(fetcher, interest, response))
        self._fetchers[subscription_id] = fetcher
        fetcher.start()

    def _on_subscription_response(self, fetcher, interest, response):
        fetcher = self._fetchers.pop(fetcher.subscription_id)
        data = Data(interest.getName())
        data.setContent(response)
        data.getMetaInfo().setFreshnessPeriod(defaults.FRESHNESS_PERIOD)
        self._producer.sendFinish(data)
