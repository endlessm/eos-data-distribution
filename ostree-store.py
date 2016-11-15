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

import SimpleStore

import gi

#gi.require_version('OSTree', '1.0')

from gi.repository import GObject
from gi.repository import GLib
#from gi.repository import OSTree

from NDN import Consumer, Producer, Endless
import Chunks

from os import path
import json

import logging
logging.basicConfig(level=Endless.LOGLEVEL)
logger = logging.getLogger(__name__)

class Store(Producer):
    def __init__(self, tempdir, repo, *args, **kwargs):
        def delget(h, a):
            ret = h[a]
            del h[a]
            return ret

        self.prefixes = prefixes = Endless.Names({p: delget(kwargs, '%s_prefix'%p)  for p in ['consumer', 'producer']})
        super(Store, self).__init__(name=prefixes.consumer, auto=True, *args, **kwargs)
        self.tempdir = tempdir
        self.repo = repo
        self.chunks = dict()

        self.store = SimpleStore.Producer(tempdir, prefixes.producer)

        self.store.connect('producer-added', self.onProducerAdded)
        self.store.connect('producer-removed', self.onProducerRemoved)

        self.consumer = Consumer(name=prefixes.consumer, *args, **kwargs)

        self.consumer.connect('data', self.getShards)

        self.connect('interest', self.onInterest)

    def onInterest(self, o, prefix, interest, face, interestFilterId, filter):
        name = interest.getName()
        subid = name.toUri().split(self.prefixes.consumer)[1]
        if not subid:
            logger.warning('Error, the requested name doesn\'t contain a sub', NDN.dumpName(name))
            return False

        self.consumer.expressInterest(path.join(self.prefixes.producer, path.basename(subid)))

    def getShards(self, consumer, interest, data):
        buf = self.dataToBytes(data)
        names = json.loads(str(buf))
        filename = lambda n: path.join(self.tempdir, path.basename(n) + '.shard')

        if not names:
            logger.warning('got no names, the sub is probably invalid')
            return False

        (self.addConsumer(n, filename(n)) for n in names)

    def addConsumer(self, n, filename):
        try:
            consumer = self.chunks[filename]
            logger.warning('already got consumer for this name', n.getUri())
            return consumer
        except:
            pass

        logger.info('spawning consumer for %s: %s', NDN.dumpName(n), filename)
        self.chunks[filename] = Chunks.Consumer(n, filename, auto=True)

    def onProducerAdded(self, name, producer, d=None):
        print name, 'added as', producer

    def onProducerRemoved(self, name, d=None):
        print name, 'removed'

if __name__ == '__main__':
    import sys
    import argparse
    from tempfile import mkdtemp

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tempdir", required=True)
    parser.add_argument("-r", "--repo", required=True)
    parser.add_argument("-c", "--consumer-prefix", default=Endless.NAMES.INSTALLED)
    parser.add_argument("-p", "--producer-prefix", default=Endless.NAMES.SOMA)

    args = parser.parse_args()
    kwargs = args.__dict__

    logger.info('creating store', kwargs)
    store = Store(**kwargs)

    GLib.MainLoop().run()
