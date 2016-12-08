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

import errno
import json
import logging
import os
import re
from os import path

import gi

from gi.repository import GObject
from gi.repository import GLib

from pyndn import Name

from eos_data_distribution import ndn, SimpleStore
from eos_data_distribution.names import SUBSCRIPTIONS_SOMA, SUBSCRIPTIONS_INSTALLED
from eos_data_distribution.ndn.file import FileConsumer
from eos_data_distribution.soma_subscription_fetcher import getSubIdName

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParallelConsumer(GObject.GObject):
    __gsignals__ = {
        'complete': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, consumers):
        self._incomplete_consumers = set(consumers)
        for consumer in self._incomplete_consumers:
            consumer.connect('complete', self._on_consumer_complete)

    def _on_consumer_complete(self, consumer):
        self._incomplete_consumers.remove(consumer)
        if len(self._incomplete_consumers) == 0:
            self.emit('complete')


class SubscriptionFetcher(GObject.GObject):
    __gsignals__ = {
        'complete': (GObject.SIGNAL_RUN_FIRST, None, (str, )),
    }

    def __init__(self, face, store_dir, subscription_id):
        self.subscription_id = subscription_id

        self._face = face
        self._store_dir = store_dir

        self._manifest_filename = path.join(self._store_dir, self.subscription_id, 'manifest.json')
        self._shard_filenames = []

    def _fetch_manifest(self):
        manifest_ndn_name = "%s/%s/manifest.json" % (SUBSCRIPTIONS_SOMA, self.subscription_id, 'manifest.json')

        out_file = open(self._manifest_filename, 'wb')

        manifest_consumer = FileConsumer(manifest_ndn_name, self._manifest_filename, auto=True)
        manifest_consumer.connect('complete', self._fetch_manifest_complete)

    def _fetch_manifest_complete(self, consumer):
        with open(self._manifest_filename, 'r') as f:
            manifest = json.load(f)

        consumers = []
        for shard in manifest['shards']:
            postfix = 'shards/%s' % (re.sub('https?://', '', shard['download_uri']))
            shard_ndn_name = Name("%s/%s") % (SUBSCRIPTIONS_SOMA, postfix)
            shard_filename = path.realpath(path.join(self._store_dir, postfix))
            self._shard_filenames.append(shard_filename)
            consumers.append(FileConsumer(subname, shard_filename, face=face, auto=True))

        parallel_consumer = ParallelConsumer(consumers)
        parallel_consumer.connect('complete', self._on_shards_complete)

    def _on_shards_complete(self):
        response = {
            "subscription_id": self.subscription_id,
            "manifest_path": self._manifest_filename,
            "shards": self._shard_filenames,
        }

        self.emit('complete', json.dumps(response))


# The SubscriptionsProducer listens for intents to /endless/installed/foo,
# downloads the manifest and shards by fetching from /endless/soma/v1/foo/...,
# and then generates a "signalling response" for them.
class SubscriptionsProducer(object):
    def __init__(self, store_dir):
        self._store_dir = store_dir
        self._fetchers = {}

        self._producer = ndn.Producer(SUBSCRIPTIONS_INSTALLED)
        self._producer.connect('interest', self._on_interest)

    def start(self):
        self._producer.registerPrefix()

    def _on_interest(self, o, prefix, interest, face, interestFilterId, filter):
        name = interest.getName()
        subscription_id = getSubIdName(name, SUBSCRIPTIONS_INSTALLED)

        if subscription_id in self._fetchers:
            return

        fetcher = SubscriptionFetcher(face, self._store_dir, subscription_id)
        fetcher.connect('complete', lambda fetcher, response: self._on_subscription_complete(fetcher, interest, response))
        self._fetchers[subscription_id] = fetcher

    def _on_subscription_complete(self, fetcher, interest, response):
        fetcher = self._fetchers.pop(fetcher.subscription_id)
        self._producer.send(interest.getName(), response)


if __name__ == '__main__':
    import sys
    import argparse
    from tempfile import mkdtemp

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--store-dir", required=True)

    args = parser.parse_args()
    subscriptions_producer = SubscriptionsProducer(args.store_dir)
    store = SimpleStore.Producer(base=args.store_dir, prefix=SUBSCRIPTIONS_INSTALLED)

    GLib.MainLoop().run()
