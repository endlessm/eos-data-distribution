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

from Chunks import Producer

from os import path

class Getter(Producer):
    def __init__(self, name,
                 base = 'https://subscriptions.prod.soma.endless-cloud.com',
                 *args, **kwargs):
        super(Getter, self).__init__(name, *args, **kwargs)
        self.base = base
        self.subs = dict()
        self.names = dict()
        self.session = requests.Session()
        self.flags = ForwardingFlags()
        self.flags.setChildInherit(True)

    def getChunk(self, name, n, prefix):
        """
        Convert data requests to urls like:
        "https://subscriptions.prod.soma.endless-cloud.com/v1/10521bb3a18b573f088f84e59c9bbb6c2e2a1a67/manifest.json"
        """
        import re
        shard = self.names[prefix]
        print ("getChunk", prefix, n, shard)
        bytes = (n*self.chunkSize, (n+1)*self.chunkSize)
        r = self.session.get (shard['download_uri'],
                          headers = {'Range': 'bytes=%d-%d'%bytes})
        return r.text

    def publish(self, subId):
        try:
            sub = self.subs[subId]
        except:
            sub = self.subs[subId] = self.getSubscription(subId)

        try:
            prefixes = sub['prefixes']
        except:
            prefixes = sub['prefixes'] = dict()

        for shard in sub['shards']:
            print ('got shard', shard)
            postfix = 'v1/%s/shards/%s/%s' % (subId, shard['path'], shard['sha256_csum'])
            name = self.registerPrefix(postfix=postfix)
            prefixes[postfix] = name
            self.names[name] = shard

        self.subs[subId]['prefixes'] = prefixes

    def getSubscription(self, id):
        print 'base: %s' %self.base
        url = "%s/v1/%s/manifest.json" % (self.base, id)
        r = self.session.get(url)
        return r.json()

if __name__ == '__main__':
    from gi.repository import GLib
    import time

    EG = Getter('/endless/soma')
    print EG.publish('10521bb3a18b573f088f84e59c9bbb6c2e2a1a67')

    GLib.MainLoop().run()

