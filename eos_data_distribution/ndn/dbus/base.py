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

dbus_producer_instances = dict()

def get_route_component(base):
    if str(base).startswith(str(SUBSCRIPTIONS_BASE)):
        return base[len(SUBSCRIPTIONS_BASE)]
    else:
        return 'custom'

def sanitize_dbus_path(path):
    return (path.replace(':', '_')
               .replace('-', '_')
               .replace('.', '_'))

def build_dbus_path(name):
    return sanitize_dbus_path(DBUS_PATH_TEMPLATE % (BASE_DBUS_PATH, str(name).strip('/')))

def build_dbus_name(base, name):
    component = get_route_component(name)

    if component in ['soma', 'installed']:
        return base + '.' + component
    return base

class Base(GObject.GObject):
    """Base class

    All this is a lie, we put here all the boilerplate code we need to have
    our clases behave like the real chunks

    """
    def __init__(self, name,
                 chunk_size=CHUNK_SIZE,
                 cost=RouteCost.DEFAULT,
                 face=None):
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
                 object_manager_class=EosDataDistributionDbus.ObjectManagerClient,
                 *args, **kwargs):
        self._wants_start = False
        self._pending_interests = dict()
        self._object_manager = None
        self._dbus_name = build_dbus_name(dbus_name, name)
        dbus_path = BASE_DBUS_PATH # build_dbus_path(name)

        super(Consumer, self).__init__(name=name, *args, **kwargs)

        logger.debug('spawning ObjectManagerClient on %s %s %s', name, self._dbus_name, dbus_path)
        object_manager_class.new_for_bus(
            BUS_TYPE, Gio.DBusObjectManagerClientFlags.NONE,
            self._dbus_name, dbus_path,
            callback=self._on_manager_ready)

    def _on_manager_ready(self, proxy, res):
        self._object_manager = Gio.DBusObjectManagerClient.new_for_bus_finish(res)

        if self._wants_start:
            self.expressInterest(self.interest, try_again=True)
            self._wants_start = False

    def _flush_pending_interests(self, manager, obj, d=None):
        logger.debug('processing pending interests: %s', self._pending_interests)
        for i in self._pending_interests:
             interest, dbus_path, dbus_name = i
             if self._dbus_express_interest(interest, dbus_path, dbus_name):
                del self._pending_interests[interest]

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
        found = self._dbus_express_interest(interest, dbus_path, self._dbus_name)
        if not found and try_again:
            try:
                return self._pending_interests[interest]
            except KeyError:
                self._pending_interests[interest] = (interest, dbus_path, self._dbus_name)

    def _dbus_express_interest(self, interest, dbus_path, dbus_name):
        logger.debug('looking for %s in %s (%s)', dbus_path, [p.get_object_path() for p in self._object_manager.get_objects()], self._object_manager)
        prefix = interest
        while len(prefix):
            object_path = build_dbus_path(prefix)
            proxy = self._object_manager.get_object(object_path)
            if proxy:
                break

            logger.debug("couldn't find %s on bus", object_path)
            prefix = '/'.join(prefix.split('/')[:-1])

        if not len(prefix):
            logger.debug("failed to find a dbus object for %s %s %s", interest, dbus_name, dbus_path)
            return None

        interface = proxy.get_interfaces()[0]
        logger.info('found proxy for: %s ↔ %s, will export %s', dbus_path, object_path, interface)

        return self._do_express_interest(proxy, interface, interest)

    def _do_express_interest(self,  proxy, interface, interest):
        return interface.RequestInterest('(s)', interest, result_handler=self._on_call_complete)

    def _on_call_complete(self, proxy, res, *a):
        logger.info('call complete, %s', res)
        interest, data = res
        self.emit('data', interest, data)
        self.emit('complete')

class DBusProducerSingleton():
    def __init__(self, name, dbus_name, skeleton):
        self._cb_registery = dict()
        self._obj_registery = dict()
        self._dbus_name = build_dbus_name(dbus_name, name)
        self._interface_skeleton_object = skeleton

        self.con = Gio.bus_get_sync(BUS_TYPE, None)

        dbus_path = BASE_DBUS_PATH # build_dbus_path(name)

        logger.debug('Producer ObjectManagerServer dbus: %s, %s', dbus_path, self._dbus_name)
        self._object_manager = Gio.DBusObjectManagerServer(object_path=dbus_path)
        self._object_manager.set_connection(self.con)

        Gio.bus_own_name_on_connection(
            self.con, self._dbus_name, Gio.BusNameOwnerFlags.NONE, None, None)

    def register_path_for_name(self, name, cb):

        interface_skeleton = self._interface_skeleton_object()
        interface_skeleton.connect('handle-request-interest',
                       self._on_request_interest)

        dbus_path = build_dbus_path(name)
        logger.debug('Producer Object dbus path: %s', dbus_path)
        object_skeleton = Gio.DBusObjectSkeleton()
        object_skeleton.set_object_path(dbus_path)
        object_skeleton.add_interface(interface_skeleton)

        logger.debug('registering path: %s ↔ %s', dbus_path,
                     interface_skeleton.get_object_path())
        registered = self._object_manager.export(object_skeleton) or True
        iface_str = interface_skeleton.get_info().name

        if not registered:
            return logger.error('got error: %s, %s, %s, %s',
                         registered, self._dbus_name, dbus_path,
                                iface_str)

        self._cb_registery[str(name)] = cb
        logger.info('registered: %s, %s, %s',
                    self._dbus_name, dbus_path, iface_str)
        return registered

    def _on_request_interest(self, skeleton, invocation, name, *args, **kwargs):
        logger.debug('RequestInterest: name=%s, cb_registery=%s', name, self._cb_registery)

        self._obj_registery[str(name)] = (skeleton, invocation)

        prefix = str(name)
        while len(prefix):
            try:
                cb = self._cb_registery[prefix]
                break
            except KeyError:
                logger.debug("couldn't find handler for %s", prefix)
                prefix = '/'.join(prefix.split('/')[:-1])

        cb(name, skeleton,  *args, **kwargs)
        return True

    def return_value(self, name, *args, **kwargs):
        skeleton, invocation = self._obj_registery[str(name)]
        logger.debug('returning value for %s on %s', name, invocation)
        skeleton.complete_request_interest(invocation, *args, **kwargs)

    def return_error(self, name, error):
        skeleton, invocation = self._obj_registery[str(name)]
        logger.debug('returning ERROR %s for %s on %s', error, name, invocation)
        invocation.return_gerror(GLib.GError(error))

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
                 skeleton=EosDataDistributionDbus.BaseProducerSkeleton,
                 *args, **kwargs):
        self.registered = False
        self._workers = dict()

        super(Producer, self).__init__(name=name, *args, **kwargs)
        try:
            self._dbus = dbus_producer_instances[dbus_name]
        except KeyError:
            self._dbus = dbus_producer_instances[dbus_name] = DBusProducerSingleton(name, dbus_name, skeleton)

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
    parser.add_argument("-c", "--consumers", default=3)
    parser.add_argument("-p", "--producers", default=10)
    args = utils.parse_args(parser=parser)

    producers = [Producer(Name('/endlessm/name%s'%(i)))
                 for i in range(int(args.producers))]
    consumers = [Consumer(Name('/endlessm/name%s'%(i)))
                 for i in range(int(args.consumers))]
    [p.connect('interest', lambda i, n, *a: p.send(n, n)) for p in producers]
    [p.start() for p in producers]

    [c.connect('complete', on_complete) for c in consumers]
    [c.start() for c in consumers]

    loop.run()
