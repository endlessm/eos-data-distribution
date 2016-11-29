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

import NDN

from NDN import Endless
import logging
logging.basicConfig(level=Endless.LOGLEVEL)
logger = logging.getLogger(__name__)

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

    def __init__(self, face = Face(), klass=None, tick=100):
        GObject.GObject.__init__(self)
        self.tick = tick
        self.face = face
        self.pool = dict()
        self.klass = klass

class Producer(Pool):
    def __init__(self, klass = NDN.Producer, *args, **kwargs):
        super(Producer, self).__init__(klass=klass, *args, **kwargs)

    def add(self, *args, **kwargs):
        logger.info ('adding producer: %s %s', args, kwargs)
        # kwargs['face'] = self.face
        (name, filename) = args
        producer = self.klass(*args, **kwargs)
        producer.registerPrefix()
        self.pool[name] = producer

        producer.connect('register-success', lambda n, p, d=None:
                    self.emit('added', name, producer))
        producer.connect('register-failed', lambda n, d=None:
                    self.remove(name))

    def remove(self, name):
        logger.info ('removing producer: %s', name)
        producer = self.pool[name]
        producer.removeRegisteredPrefix(name)
        self.emit('removed', name)

class Consumer(Pool):
    def __init__(self, klass=NDN.Consumer, *args, **kwargs):
        super(Consumer, self).__init__(klass=klass, *args, **kwargs)

    def add(self, *args, **kwargs):
        logger.info ('adding consumer: %s %s', args, kwargs)
        kwargs['face'] = self.face
        (name, filename) = args
        consumer = self.klass(*args, **kwargs)
        consumer.expressInterest()
        self.pool[name] = consumer
        self.emit('added', name, consumer)

    def remove(self, name):
        logger.info ('removing consumer: %s', name)
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

    def __init__(self, producerKlass = NDN.Producer,
                 consumerKlass = NDN.Consumer,
                 *args, **kwargs):
        super(MixPool, self).__init__(*args, **kwargs)
        self.producer = Producer(klass=producerKlass, *args, **kwargs)
        self.consumer = Consumer(klass=consumerKlass, *args, **kwargs)

        self.producers = dict()
        self.consumers = dict()

        self.producer.connect('removed', lambda p, d=None: self.emit('producer-removed', p))
        self.producer.connect('added', lambda p, P, d=None: self.emit('producer-added', p, P))
        self.consumer.connect('removed', lambda p, d=None: self.emit('consumer-removed', p))
        self.consumer.connect('added', lambda p, P, d=None: self.emit('consumer-added', p, P))

    def get_producer(self):
        return self.producer

    def get_consumer(self):
        return self.consumer

    def add_producer(self, *args, **kwargs):
        return self.producer.add (*args, **kwargs)

    def add_consumer(self, *args, **kwargs):
        return self.consumer.add (*args, **kwargs)

    def remove_producer(self, *args, **kwargs):
        return self.producer.remove (*args, **kwargs)

    def remove_consumer(self, *args, **kwargs):
        self.consumer.remove (*args, **kwargs)
