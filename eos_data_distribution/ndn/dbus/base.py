# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2017 Endless Mobile Inc.
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
import gi

gi.require_version('EosDataDistributionDbus', '0')
from gi.repository import EosDataDistributionDbus

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

from ...defaults import CHUNK_SIZE, RouteCost
from ...names import Name, SUBSCRIPTIONS_BASE

logger = logging.getLogger(__name__)

BUS_TYPE = Gio.BusType.SESSION

BASE_DBUS_NAME = 'com.endlessm.NDNHackBridge.base'
BASE_DBUS_PATH = '/com/endlessm/NDNHackBridge'

DBUS_PATH_TEMPLATE = '%s/%s'

def get_dbusable_name(base):
    if str(base).startswith(str(SUBSCRIPTIONS_BASE)):
        return SUBSCRIPTIONS_BASE[-1]
    else:
        return 'custom'

def build_dbus_path(name):
    return DBUS_PATH_TEMPLATE % (BASE_DBUS_PATH, str(name)
                                 .replace(':', '_')
                                 .replace('-', '_')
                                 .replace('.', '_')
                                 .strip('/'))

class Base(GObject.GObject):
    """Base class

    All this is a lie, we put here all the boilerplate code we need to have
    our clases behave like the real chunks

    """
    def __init__(self, name,
                 chunk_size=CHUNK_SIZE,
                 cost=RouteCost.DEFAULT):
        GObject.GObject.__init__(self)
        self.chunk_size = chunk_size
        self.cost = cost
        self.name = name

class Interest(str):
    """Fake Interest Class

    This mimics NDN's Interest class as much as we need

    """

    def __init__(self, name=None):
        super(Interest, self).__init__(name)

    def size(self):
        return self.count('/')

    def getName(self):
        return Name(self)

class Consumer(Base):
    """Base DBus-NDN consumer

    this is for simple message passing with the NDN API
    """

    __gsignals__ = {
        'data': (GObject.SIGNAL_RUN_FIRST, None, (str, object, )),
        'progress': (GObject.SIGNAL_RUN_FIRST, None, (int, )),
        'complete': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, name, dbus_name = BASE_DBUS_NAME,
                 object_path=BASE_DBUS_PATH,
                 *args, **kwargs):
        self._object_manager = None
        self._wants_start = False
        self.DBUS_NAME = dbus_name

        super(Consumer, self).__init__(name=name, *args, **kwargs)

        Gio.DBusObjectManagerClient.new_for_bus(
            BUS_TYPE, Gio.DBusObjectManagerClientFlags.NONE, dbus_name, object_path,
            None, None, None,
            self._on_manager_ready)

    def _on_manager_ready(self, proxy, res):
        self._object_manager = Gio.DBusObjectManagerClient.new_for_bus_finish(res)

        if self._wants_start:
            self.expressInterest(self.interest, try_again=True)
            self._wants_start = False

#        Gio.bus_watch_name(BUS_TYPE, self.DBUS_NAME,
#                           Gio.BusNameWatcherFlags.AUTO_START,
#                           self._name_appeared_cb,
#                           self._name_vanished_cb)

    def start(self):
        self.expressInterest(try_again=True)

    def expressInterest(self, interest=None, try_again=False):
        if not interest:
            interest = str(self.name)

        self.interest = interest
        if not self._object_manager:
            # come back when you have someone to talk too
            self._wants_start = True
            return

        dbus_path = build_dbus_path(str(interest))

        self._dbus_express_interest(interest, dbus_path, self.DBUS_NAME)

    def _dbus_express_interest(self, interest, dbus_path, dbus_name):
        proxy = self._object_manager.get_object(dbus_path)
        iproxy = proxy.get_interfaces()[0]
        logger.info('looking for proxy for: %s ↔ %s', dbus_path, iproxy.get_name())
        iproxy.call_request_interest(self.interest, None, self._on_call_complete)

#        EosDataDistributionDbus.BaseProducerProxy.new(
#            self.con, Gio.DBusProxyFlags.NONE, dbus_name, dbus_path, None,
#            self._on_proxy_ready)

    def _on_call_complete(self, proxy, res):
        interest, data = proxy.call_request_interest_finish(res)
        self.emit('data', interest, data)
        self.emit('complete')

dbus_instances = dict()

class DBusInstance():
    def __init__(self, name, skeleton, object_manager = Gio.DBusObjectManagerServer(object_path=BASE_DBUS_PATH)):
        self._cb_registery = dict()
        self._obj_registery = dict()
        self.DBUS_NAME = name
        self._interface_skeleton = skeleton
        self._interface_skeleton.connect('handle-request-interest',
                                         self._on_request_interest)

        self.con = Gio.bus_get_sync(BUS_TYPE, None)

        self._object_manager = object_manager
        self._object_manager.set_connection(self.con)

        Gio.bus_own_name_on_connection(
            self.con, self.DBUS_NAME, Gio.BusNameOwnerFlags.NONE, None, None)

    def register_path_for_name(self, name, cb):
        dbus_path = build_dbus_path(name)
        object_skeleton = Gio.DBusObjectSkeleton()
        object_skeleton.set_object_path(dbus_path)
        object_skeleton.add_interface(self._interface_skeleton)

        logger.debug('registering path: %s ↔ %s', dbus_path,
                     self._interface_skeleton.get_object_path())
        registered = self._object_manager.export(object_skeleton) or True
        iface_str = self._interface_skeleton.get_info().name

        if not registered:
            return logger.error('got error: %s, %s, %s, %s',
                         registered, self.DBUS_NAME, dbus_path,
                                iface_str)

        self._cb_registery[str(name)] = cb
        logger.info('registered: %s, %s, %s',
                    self.DBUS_NAME, dbus_path, iface_str)
        return registered

    def _on_request_interest(self, skeleton, invocation, name, *args, **kwargs):
        logger.debug('RequestInterest: name=%s', name)

        self._obj_registery[str(name)] = (skeleton, invocation)
        self._cb_registery[str(name)](name, skeleton,  *args, **kwargs)
        return True

    def return_value(self, name, *args, **kwargs):
        skeleton, invocation = self._obj_registery[str(name)]
        logger.debug('returning value for %s on %s', name, invocation)
        skeleton.complete_request_interest(invocation, *args, **kwargs)


class Producer(Base):
    """Base DBus-NDN producer

    this is for simple message passing with the NDN API
    """

    __gsignals__ = {
        'register-failed': (GObject.SIGNAL_RUN_FIRST, None, (object, )),
        'register-success': (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        'interest': (GObject.SIGNAL_RUN_FIRST, None, (object, object, object, object, object))
    }


    def __init__(self, name, dbus_name=BASE_DBUS_NAME,
                 skeleton=EosDataDistributionDbus.BaseProducerSkeleton(),
                 *args, **kwargs):
        self.registered = False
        self._workers = dict()

        logger.debug("registering producer on name: %s, %s", name, dbus_name)

        super(Producer, self).__init__(name=name, *args, **kwargs)
        try:
            self._dbus = dbus_instances[dbus_name]
        except KeyError:
            self._dbus = dbus_instances[dbus_name] = DBusInstance(dbus_name, skeleton)

    def start(self):
        self.registerPrefix()

    def registerPrefix(self, prefix=None):
        if prefix:
            # XXX: prefix registeration is handled checking that the prefix
            # is a strict subname, but 'strict' is still to be defined
            logger.error("We don't support prefix registeration")
            raise NotImplementedError()

        if self.registered:
            console.error('already registered')
            return

        self.registred = self._dbus.register_path_for_name(self.name, self._on_request_interest)
        if not self.registred: self.emit('register-failed', self.registered)

    def send(self, name, data, flags = {}):
        logger.debug('producer: sending on name %s, %s', name, data)
        self._dbus.return_value(name, str(name), data)

    def sendFinish(self, data):
        self._dbus.return_value(name, str(self.name), data)

    def _on_request_interest(self, name, skeleton):
        logger.debug('producer: got interest for name %s, %s', name, self)
        self.emit('interest', name, Interest(name), None, None, None)

if __name__ == '__main__':
    import argparse
    from ..tests import utils as testutils
    from ... import utils

    loop = GLib.MainLoop()

    def dump(*a):
        print(a)

    def on_complete(i, *a):
        del(consumers[consumers.index(i)])
        len(consumers) or loop.quit()


    parser = argparse.ArgumentParser()
    args = utils.parse_args(parser=parser)
    producers = [Producer('/endlessm/%s'%(i)) for i in range(1)]
    consumers = [Consumer('/endlessm/%s'%(i)) for i in range(3)]
    [p.start() for p in producers]
    [p.connect('interest', lambda i, n, *a: p.send(n, n)) for p in producers]
    [c.start() for c in consumers]
    [c.connect('complete', on_complete) for c in consumers]

    loop.run()
