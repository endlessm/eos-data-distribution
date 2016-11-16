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

from pyndn import Name
from pyndn import Data
from pyndn import Face

from pyndn import ForwardingFlags

import requests

import NDN
import Chunks

from os import path
import json

from NDN import Endless

import logging
logging.basicConfig(level=Endless.LOGLEVEL)
logger = logging.getLogger(__name__)

def dump(*args, **kwargs):
    print 'DUMP', args, kwargs

class Getter(NDN.Producer):
    def __init__(self, name,
                 *args, **kwargs):
        super(Getter, self).__init__(name=name, *args, **kwargs)

        self.getters = dict()

        self.flags = ForwardingFlags()
        self.flags.setChildInherit(True)

        self.connect('interest', self.onInterest)

    def onInterest(self, o, prefix, interest, face, interestFilterId, filter):
        name = interest.getName()
        subid = name.getSubName(self.name.size())
        logger.info ('subid is: %s', NDN.dumpName(subid))

        logger.info('interest: %s, on %s for %s', NDN.dumpName(name), self.name, subid)
        if not subid:
            logger.warning('Error, the requested name doesn\'t contain a sub: %s', NDN.dumpName(name))
            return False

        substr = str(subid.get(0))
        try:
            # we still register, because this might be asking for an old
            # subscription that we lost track of. Note that this is racy,
            # because there is no getter associated (yet), if we have
            # registered, this is a noop, is subscribe.
            self.getters[substr].publish()
            logger.warning('Error, we got a path, expected a subid: %s', subid)
            return False
        except:
            pass

        self.getters[substr] = ChunksGetter(name=name, basename=self.name)
        return True

    def sendLinks(self, name, names):
        link = Link(Data(name))
        [link.addDelegation(0, Name(n)) for n in names]
        self.sendFinish(link)

class ChunksGetter(Chunks.Producer):
    def __init__(self, name, basename=None,
                 base = 'https://subscriptions.prod.soma.endless-cloud.com',
                 *args, **kwargs):
        name.append ('shards')
        super(ChunksGetter, self).__init__(name, *args, **kwargs)
        self.base = base
        self.subs = dict()
        self.subprefixes = dict()
        self.names = dict()
        self.session = requests.Session()

        if basename:
            self.subid = name.getSubName(basename.size()).get(0)
            self.registerPrefix(name)
            names = self.publish()

            # wait for registration success before sending the list of
            # names, the actual registration is done by Chunks -> NDN
            # classes.
            self.connect('register-success', lambda *args, **kwargs:
                         self.send(name, json.dumps(names)))

    def getChunk(self, name, n, prefix):
        """
        Convert data requests to urls like:
        "https://subscriptions.prod.soma.endless-cloud.com/v1/10521bb3a18b573f088f84e59c9bbb6c2e2a1a67/manifest.json"
        """
        import re
        shard = self.names[prefix]
        bytes = tuple(i*self.chunkSize for i in (n, n+1))

        logger.debug("getChunk %d, %s, %s, %s", n, bytes, prefix, shard)
        r = self.session.get (shard['download_uri'],
                          headers = {'Range': 'bytes=%d-%d'%bytes})
        return r.text[:self.chunkSize]

    def publish(self, subId=None):
        if not subId: subId = self.subId

        if not isinstance(subId, str):
            subId = str(subId)

        logger.info('asked for sub: %s', subId)
        if subId in self.subs.keys():
            logger.warning('subscription already runing for %s…ignoring new request', subId)
            return self.subs[subId]

        sub = self.subs[subId] = self.getSubscription(subId)
        if not sub:
            logger.warning('This sub is invalid: %s', subId)
            return sub

        prefixes = dict()
        ret = []

        for shard in sub['shards']:
            logger.debug('looking at shard: %s', shard)
            postfix = '%s/shards/%s/%s' % (subId, shard['path'], shard['sha256_csum'])
            name = self.registerPrefix(postfix=postfix)
            prefixes[postfix] = name
            self.names[name] = shard
            ret.append(name.toUri())

        self.subprefixes[subId] = prefixes
        return ret

    def getSubscription(self, id):
        logger.info('base: %s', self.base)
        url = "%s/v1/%s/manifest.json" % (self.base, id)
        r = self.session.get(url)
        if r.status_code == requests.codes.ok:
            return r.json()
        else: return False

if __name__ == '__main__':
    from gi.repository import GLib
    import time

    EG = Getter(NDN.Endless.NAMES.SOMA)
    print EG.publish('10521bb3a18b573f088f84e59c9bbb6c2e2a1a67')

    GLib.MainLoop().run()

