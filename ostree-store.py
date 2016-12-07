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

from NDN import Endless
import NDN
import Chunks
from Edge import getSubIdName

from os import path
import json
import re

import logging
logging.basicConfig(level=Endless.LOGLEVEL)
logger = logging.getLogger(__name__)

try:
    gi.require_version('Notify', '0.7')
    from gi.repository import Notify
    Notify.init ("NDN Store")
except:
    Notify = False

class Store(NDN.Producer):
    def __init__(self, tempdir, *args, **kwargs):
        def delget(h, a):
            ret = h[a]
            del h[a]
            return ret

        self.prefixes = prefixes = Endless.Names({p: delget(kwargs, '%s_prefix'%p)  for p in ['consumer', 'producer']})
        super(Store, self).__init__(name=prefixes.consumer, auto=True, *args, **kwargs)
        self.tempdir = tempdir
        self.consumers = dict ()
        self.subs = dict ()
        self.interests = dict ()
        self.notifications = dict ()

        self.store = SimpleStore.Producer(tempdir, prefixes.producer)

        self.store.connect('producer-added', self.onProducerAdded)
        self.store.connect('producer-removed', self.onProducerRemoved)

        self.connect('interest', self.onInterest)

    def onInterest(self, o, prefix, interest, face, interestFilterId, filter):
        name = interest.getName()
        subid = getSubIdName (name, self.prefixes.consumer)
        ssubid = str (subid)
        manifest_path = path.join (ssubid, 'manifest.json')
        subname = "%s/%s"%(self.prefixes.producer, manifest_path)

        if not subid:
            logger.warning('Error, the requested name doesn\'t contain a sub', NDN.dumpName(name))
            return False

        try:
            ret = self.consumers [subname]
            logger.warning ('We already have a consumer for this sub: %s → %s', subid, ret)
            return ret
        except:
            pass

        self.interests [ssubid] = name
        sub = Chunks.Consumer (subname,
                               filename=path.join (self.tempdir, manifest_path),
                               auto=True)

        sub.notifyChunk ("Getting Metadata %s" % ssubid)
        sub.connect ('complete', self.getShards, ssubid)

        self.consumers [subname] = sub
        return sub

    def getShards(self, consumer, manifest_filename, subid):
        logger.info ('got shards: %s : %s', consumer, manifest_filename)

        f = open (manifest_filename, 'r')
        manifest = json.loads (f.read())

        try:
            return self.subs [subid]
        except:
            pass

        self.subs [subid] = dict ()

        for shard in manifest['shards']:
            logger.debug('looking at shard: %s', shard)
            postfix = 'shards/%s' % (re.sub ('https?://', '', shard ['download_uri']))
            subname = "%s/%s" % (Endless.NAMES.SOMA, postfix)
            shard_filename = path.join (self.tempdir, postfix)
            sub = Chunks.Consumer (subname, filename=shard_filename, auto=True)
            sub.notifyChunk ("Downloading %s" % shard_filename)
            sub.connect ('complete', self.checkSub, manifest_filename, subid)
            self.subs [subid] [shard_filename] = False

            self.consumers [subname] = sub

    def checkSub (self, consumer, shard_filename, manifest_filename, subid):
        self.subs [subid] [shard_filename] = True

        logger.info ('shard complete: %s → %s', shard_filename, subid)
        if all (self.subs [subid].values()):
            logger.info ('all shards have been downloaded: %s', self.subs [subid])
            if Notify:
                notification = Notify.Notification.new('all shards have been downloaded')
                notification.show()
        
            shard_filenames = [path.realpath(shard_filename) for shard_filename in self.subs[subid]]

            response = {
                "subscription_id": subid,
                "manifest_path": manifest_filename,
                "shards": shard_filenames,
            }

            self.send (self.interests [subid], json.dumps (response))

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
    parser.add_argument("-c", "--consumer-prefix", default=Endless.NAMES.INSTALLED)
    parser.add_argument("-p", "--producer-prefix", default=Endless.NAMES.SOMA)

    args = parser.parse_args()
    kwargs = args.__dict__

    logger.info('creating store', kwargs)
    store = Store(**kwargs)

    GLib.MainLoop().run()
