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
import operator
import os
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

DBUS_PATH_TEMPLATE = '%s%s'

ENDLESS_NDN_COMPONENT_NAMES = ('store', 'router')

dbus_producer_instances = dict()

GObject.threads_init()

def identity(*args):
    if len(args) == 1:
        return args[0]
    return args

def extend(a, b):
    a.extend(b)
    return a

def get_route_component(base):
    base = Name(base)
    if base.toString().startswith(SUBSCRIPTIONS_BASE.toString()):
        return base[len(SUBSCRIPTIONS_BASE)]
    else:
        return 'custom'

def sanitize_dbus_path(path):
    return (path.replace(':', '_')
            .replace('-', '_')
            .replace('.', '_')
            .replace('%', '_'))

def build_dbus_path(name):
    name = Name(name)
    return sanitize_dbus_path(DBUS_PATH_TEMPLATE % (BASE_DBUS_PATH, name.toString()))

def build_dbus_name(base, name):
    ret = _build_dbus_name(base, name)
    env = os.environ.get('ENDLESS_NDN_COMPONENT_NAME')
    if env:
        return ret + '.' + env
    return ret

def _build_dbus_name(base, name):
    component = get_route_component(name)

    if component in ['soma', 'installed']:
        return base + '.' + component
    return base

def find_longest_prefix_in_list(name, l, transform=identity):
    found = None
    prefix = name

    def look_up(prefix, compare):
        t = transform(prefix)
        logger.debug("looking for %s in %s, with %s", t, l, compare)
        try:
            found = [k for k in l if compare(k, t)][0]
            logger.debug("FOUND handler for %s ↔ %s", found, t)
            return found
        except IndexError:
            logger.debug("Couldn't find handler for %s", t)

        return False

    found = look_up(prefix, str.startswith)
    if found:
        return found

    prefix = '/'.join(prefix.split('/')[:-1])
    while len(prefix):
        found = look_up(prefix, operator.eq)
        if found:
            return found

        prefix = '/'.join(prefix.split('/')[:-1])

    logger.debug("FOUND NO handler for %s", name)
    return None

class Base(GObject.GObject):
    """Base class

    All this is a lie, we put here all the boilerplate code we need to have
    our clases behave like the real chunks

    """

    __gsignals__ = {
        'name-changed': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }

    def __init__(self, name,
                 chunk_size=CHUNK_SIZE,
                 cost=RouteCost.DEFAULT,
                 face=None):
        GObject.GObject.__init__(self)
        self.chunk_size = chunk_size
        self.cost = cost
        self.name = Name(name)

    def setName(self, name):
        self.name = Name(name)
        self.emit('name-changed', self.name.toString())

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
        self._pending_interests = dict()
        self._object_managers = dict()
        self._dbus_name = _build_dbus_name(dbus_name, name)
        dbus_path = BASE_DBUS_PATH # build_dbus_path(name)

        super(Consumer, self).__init__(name=name, *args, **kwargs)

        for dest in ENDLESS_NDN_COMPONENT_NAMES:
            dbus_name = self._dbus_name + '.' + dest
            logger.debug('spawning ObjectManagerClient on %s %s %s', name, dbus_name, dbus_path)
            object_manager_class.new_for_bus(
                BUS_TYPE, Gio.DBusObjectManagerClientFlags.NONE,
                dbus_name, dbus_path,
                callback=self._on_manager_ready, user_data=dest)

    def _on_manager_ready(self, proxy, res, dest):
        manager = Gio.DBusObjectManagerClient.new_for_bus_finish(res)
        if not manager.props.name_owner:
            logger.debug('object manager for %s has no name owner, dropping', dest)
            return
        logger.debug('object manager (%s) ready for %s', manager.props.name_owner, dest)
        self._object_managers[dest] = manager
        self.flush_pending_interests()

    def _flush_pending_interests(self, manager, obj, d=None):
        self.flush_pending_interests()

    def flush_pending_interests(self):
        logger.debug('processing pending interests: %s', self._pending_interests)
        for interest, dbus_path, dbus_name in self._pending_interests.values():
             if self.dbus_express_interest(interest, dbus_path, dbus_name):
                del self._pending_interests[interest]

    def start(self):
        self.expressInterest(try_again=True)

    def expressInterest(self, interest=None, try_again=False):
        if not interest:
            interest = self.name.toString()

        dbus_path = build_dbus_path(interest)

        self._pending_interests[interest] = (interest, dbus_path, self._dbus_name)
        if not len(self._object_managers):
            # come back when you have someone to talk too
            return None

        found = self.dbus_express_interest(
            interest, dbus_path, self._dbus_name)
        if not found and try_again:
            return self._pending_interests[interest]

    def dbus_express_interest(self,
                              *args, **kwargs):
        for dest in self._object_managers.keys():
            try:
                found = self._dbus_express_interest(
                    dest=dest, *args, **kwargs)
            except KeyError:
                continue

            if found: return found

    def _dbus_express_interest(self, interest, dbus_path, dbus_name, dest=None):
        object_manager = self._object_managers[dest]
        object_paths = [p.get_object_path() for p in object_manager.get_objects()]
        logger.debug('looking for %s in %s on %s.%s', dbus_path, object_paths, dbus_name, dest)

        object_path = find_longest_prefix_in_list(interest, object_paths, transform=build_dbus_path)
        if object_path == None:
            logger.debug("failed to find a dbus object for %s %s %s", interest, dbus_name, dbus_path)
            return None

        proxy = object_manager.get_object(object_path)
        interface = proxy.get_interfaces()[0]
        logger.info('found proxy for: %s ↔ %s, will export %s', dbus_path, object_path, interface)

        return self._do_express_interest(proxy, interface, interest)

    def _do_express_interest(self,  proxy, interface, interest):
        return interface.call_request_interest(interest,
                                               callback=self._on_request_interest_complete, user_data=interest)

    def _on_request_interest_complete(self, interface, res, interest):
        logger.info('call complete, %s', res)
        try:
            name, data = interface.call_request_interest_finish(res)
        except GLib.Error as error:
            # XXX actual error handeling !
            logger.debug('got: %s, asuming TryAgain', error)
            # assuming TryAgain
            return self.expressInterest(interest)

        del self._pending_interests[interest]

        self.emit('data', interest, data)
        self.emit('complete')

class DBusProducerSingleton():
    def __init__(self, name, dbus_name, skeleton):
        self._cb_registery = dict()
        self._obj_registery = dict()
        self._dbus_name = build_dbus_name(dbus_name, name)
        self._interface_skeleton_object = skeleton

        address = Gio.dbus_address_get_for_bus_sync(BUS_TYPE, None)
        self.con = Gio.DBusConnection.new_for_address_sync(address, Gio.DBusConnectionFlags.NONE, None, None)


        dbus_path = BASE_DBUS_PATH # build_dbus_path(name)

        logger.debug('Producer ObjectManagerServer dbus: %s, %s', dbus_path, self._dbus_name)
        self._object_manager = Gio.DBusObjectManagerServer(object_path=dbus_path)
        self._object_manager.set_connection(self.con)

        Gio.bus_own_name_on_connection(
            self.con, self._dbus_name, Gio.BusNameOwnerFlags.NONE, None, None)

    def register_path_for_name(self, name, callbacks):
        name = Name(name)
        interface_skeleton = self._interface_skeleton_object()
        interface_skeleton.connect('handle-request-interest',
                       self._on_request_interest)
        try:
            interface_skeleton.connect('handle-complete',
                                    self._on_complete)
        except TypeError:
            pass

        dbus_path = build_dbus_path(name)
        logger.debug('Producer Object dbus path: %s', dbus_path)
        object_skeleton = Gio.DBusObjectSkeleton()
        object_skeleton.set_object_path(dbus_path)
        object_skeleton.add_interface(interface_skeleton)

        logger.debug('registering path: %s', dbus_path)
        registered = self._object_manager.export(object_skeleton) or True
        iface_str = interface_skeleton.get_info().name

        if not registered:
            return logger.error('got error: %s, %s, %s, %s',
                         registered, self._dbus_name, dbus_path,
                                iface_str)

        key = name.toString()
        for cb in callbacks.keys():
            try:
                self._cb_registery[cb]
            except KeyError:
                self._cb_registery[cb] = dict()

            self._cb_registery[cb][key] = callbacks[cb]
        logger.info('registered: %s, %s, %s',
                    self._dbus_name, dbus_path, iface_str)
        return registered

    def _on_complete(self, *args, **kwargs):
        return self._find_handler_and_call('complete', *args, **kwargs)

    def _on_request_interest(self, *args, **kwargs):
        return self._find_handler_and_call('request-interest', *args, **kwargs)

    def _find_handler_and_call(self, handler_name, skeleton, invocation,  *args, **kwargs):
        # this is where the dbus interface is completely stupid, *if*
        # fd_list is present, it's going to come in first…

        if type(args[0]) is str:
            name = args[0]
            fd_list = None
            args = args[1:]

        else:
            name = args[1]
            fd_list = args[0]
            args = extend([fd_list], args[2:])

        self._obj_registery[name] = (skeleton, invocation, fd_list)

        logger.debug('handeling call %s for name=%s, args=%s, kwargs=%s',
                     handler_name, name, args, kwargs)
        logger.debug('cb_registery: %s', self._cb_registery)

        prefix = find_longest_prefix_in_list(name, self._cb_registery[handler_name].keys())
        if prefix:
            callback = self._cb_registery[handler_name][prefix]
            return callback(Name(name), skeleton, *args, **kwargs)

    def return_value(self, name, *args, **kwargs):
        key = name.toString()
        skeleton, invocation, fd_list = self._obj_registery[key]
        logger.debug('returning value for %s on %s: %s — %s', name, invocation, args, fd_list)

        args = extend([key], args)
        if fd_list: # this looks ridiculous, but fd_list handeling is absolutely borken
            args = extend([fd_list], args)

        skeleton.complete_request_interest(invocation, *args, **kwargs)
        return True

    def return_error(self, name, error):
        skeleton, invocation, fd_list = self._obj_registery[name.toString()]
        logger.debug('returning ERROR %s for %s on %s', error, name, invocation)
        invocation.return_gerror(GLib.GError(error))
        return True

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

        self.registred = self._dbus.register_path_for_name(self.name, {
            'request-interest': self._on_request_interest,
            'complete': self._on_complete
        })
        if not self.registred: self.emit('register-failed', self.registered)

    def send(self, name, data, flags = {}):
        logger.debug('producer: sending on name %s, %s', name, data)
        self._dbus.return_value(name, name.toString(), data)

    def sendFinish(self, name, data):
        self._dbus.return_value(name, name.toString(), data)

    def _on_request_interest(self, name, skeleton):
        logger.debug('producer: got interest for name %s ↔ %s', name, self.name)
        self.emit('interest', name, Interest(name), None, None, None)
        return True

    def _on_complete(self, name, skeleton):
        raise NotImplemented

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

    [p.connect('interest', lambda i, n, *a: p.send(n, n.toString())) for p in producers]
    [p.start() for p in producers]

    [c.connect('complete', on_complete) for c in consumers]
    [c.start() for c in consumers]

    loop.run()
