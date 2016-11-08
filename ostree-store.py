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

class Store(GObject.GObject):
    def __init__(self, tempdir, prefix, repo):
        GObject.GObject.__init__(self)
        self.store = SimpleStore.Producer(tempdir, prefix)
        self.store.connect('producer-added', self.onProducerAdded)
        self.store.connect('producer-removed', self.onProducerRemoved)

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
    parser.add_argument("-p", "--prefix", default="/endless/soma/v1/")

    args = parser.parse_args()
    kwargs = args.__dict__

    print 'creating store', kwargs
    store = Store(**kwargs)

    GLib.MainLoop().run()
