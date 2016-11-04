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

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GObject
from gi.repository import GLib

from pyndn.security import KeyChain

from pyndn import Name
from pyndn import Data
from pyndn import Face

import Chunks

from os import path
from functools import partial

SIGNALS = ['added', 'removed']

class Pool(GObject.GObject):
    __gsignals__ = {
        'added': (GObject.SIGNAL_RUN_FIRST, None,
                  (object, object)),
        'removed': (GObject.SIGNAL_RUN_FIRST, None,
                    (object,)),
    }

    def __init__(self, face = Face(), tick=100):
        GObject.GObject.__init__(self)
        self.tick = tick
        self.face = face
        self.pool = dict()

        # if no MainLoop is added this should be free right ?
        GLib.timeout_add(self.tick, self.processEvents)

    def processEvents(self):
        self.face.processEvents()
        return True

class Producer(Pool):
    def __init__(self, *args, **kwargs):
        super(Producer, self).__init__(*args, **kwargs)

    def add(self, *args, **kwargs):
        kwargs['face'] = self.face
        (name, filename) = args
        producer = Chunks.Producer(*args, **kwargs)
        producer.registerPrefix()
        self.pool[name] = producer
        self.emit('added', name, producer)

    def remove(self, name):
        producer = self.pool[name]
        producer.removeRegisteredPrefix(name)
        self.emit('removed', name)


class Consumer(Pool):
    def __init__(self, *args, **kwargs):
        super(Consumer, self).__init__(*args, **kwargs)

    def add(self, *args, **kwargs):
        kwargs['face'] = self.face
        (name, filename) = args
        consumer = Chunks.Consumer(*args, **kwargs)
        consumer.expressInterest()
        self.pool[name] = consumer
        self.emit('added', name, consumer)

    def remove(self, name):
        consumer = self.pool[name]
        consumer.removePendingInterest(name)
        self.emit('removed', name)

class MixPool(GObject.GObject):
    __gsignals__ = {
        'producer-added': (GObject.SIGNAL_RUN_FIRST, None,
                  (object, object)),
        'producer-removed': (GObject.SIGNAL_RUN_FIRST, None,
                    (object,)),
        'consumer-added': (GObject.SIGNAL_RUN_FIRST, None,
                  (object, object)),
        'consumer-removed': (GObject.SIGNAL_RUN_FIRST, None,
                    (object,)),
    }

    def __init__(self, *args, **kwargs):
        super(MixPool, self).__init__()

        self.producer = Producer(*args, **kwargs)
        self.consumer = Consumer(*args, **kwargs)

        [self.producer.connect(s, lambda *args, **kwargs: self.emit('producer-%s'%s, *args, **kwargs)) for s in SIGNALS]
        [self.consumer.connect(s, lambda *args, **kwargs: self.emit('consumer-%s'%s, *args, **kwargs)) for s in SIGNALS]

