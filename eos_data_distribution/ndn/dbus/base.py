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

IFACE_TEMPLATE = '''<node>
<interface name='%s'>
<method name='RequestInterest'>
    <arg type='s' direction='in'  name='name' />
    <arg type='s' direction='out' name='name' />
    <arg type='s' direction='out' name='data' />
</method>
</interface>
</node>''' % (BASE_DBUS_NAME)

def get_dbusable_name(base):
    if str(base).startswith(str(SUBSCRIPTIONS_BASE)):
        return SUBSCRIPTIONS_BASE[-1]
    else:
        return 'custom'

def build_dbus_path(name):
    return DBUS_PATH_TEMPLATE % (BASE_DBUS_PATH, str(name).replace('-', '_').strip('/'))

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
                 *args, **kwargs):
        self.con = None
        self._wants_start = False
        self.DBUS_NAME = dbus_name

        super(Consumer, self).__init__(name=name, *args, **kwargs)
        dbusable_name = get_dbusable_name(name)
        Gio.bus_watch_name(BUS_TYPE, self.DBUS_NAME,
                           Gio.BusNameWatcherFlags.AUTO_START,
                           self._name_appeared_cb,
                           self._name_vanished_cb)

    def _name_appeared_cb(self, con, name, owner):
        logger.info('name: %s, appeared, owned by %s', name, owner)
        self.con = con
        if self._wants_start:
            self.expressInterest(self.interest, try_again=True)
            self._wants_start = False

    def _name_vanished_cb(self, con, name):
        self.con = None

    def start(self):
        self.expressInterest(try_again=True)

    def expressInterest(self, interest=None, try_again=False):
        if not interest:
            interest = str(self.name)

        self.interest = interest
        if not self.con:
            # come back when you have someone to talk too
            self._wants_start = True
            return

        dbus_path = build_dbus_path(str(interest))

        self._dbus_express_interest(interest, dbus_path, self.DBUS_NAME)

    def _dbus_express_interest(self, interest, dbus_path, dbus_name):
        args = GLib.Variant('(s)', (str(interest),))
        self.con.call(dbus_name, dbus_path, dbus_name, 'RequestInterest',
                      args, None, Gio.DBusCallFlags.NONE, -1, None,
                      self._on_call_complete)

    def _on_call_complete(self, source, res):
        interest, data = self.con.call_finish(res).unpack()
        self.emit('data', interest, data)
        self.emit('complete')

dbus_instances = dict()

class DbusInstance():
    def __init__(self, name, iface_template):
        self._cb_registery = dict()
        self._obj_registery = dict()
        self.DBUS_NAME = name
        self.IFACE_TEMPLATE = iface_template
        self.con = Gio.bus_get_sync(BUS_TYPE, None)

        self.iface_info = Gio.DBusNodeInfo.new_for_xml(
            self.IFACE_TEMPLATE
        ).interfaces[0]

        Gio.bus_own_name_on_connection(
            self.con, self.DBUS_NAME, Gio.BusNameOwnerFlags.NONE, None, None)

    def register_path_for_name(self, name, cb):
        dbus_path = build_dbus_path(name)

        logger.debug('registering path: %s', dbus_path)
        registered = self.con.register_object(
            object_path=dbus_path,
            interface_info=self.iface_info, method_call_closure=self._on_method_call)

        if not registered:
            return logger.error('got error: %s, %s, %s, %s',
                         registered, self.DBUS_NAME, dbus_path,
                         self.IFACE_TEMPLATE)


        self._cb_registery[str(name)] = cb
        logger.info('registered: %s, %s, %s',
                    self.DBUS_NAME, dbus_path, self.IFACE_TEMPLATE)
        return registered

    def _on_method_call(self, connection, sender, object_path, interface_name, method_name, parameters, invocation):
        # Dispatch.
        getattr(self, 'impl_%s' % (method_name, ))(connection, sender, object_path, interface_name, method_name, parameters, invocation)

    def impl_RequestInterest(self, connection, sender, object_path, interface_name, method_name, parameters, invocation):
        name, = parameters.unpack()
        logger.debug('GOT RequestInterest: %s, %s', name, self)

        self._obj_registery[str(name)] = (sender, object_path, interface_name, method_name, parameters, invocation)
        self._cb_registery[str(name)](name)


    def return_value(self, name, variant):
        print 'obj reg', self._obj_registery

        sender, object_path, interface_name, method_name, parameters, invocation = self._obj_registery[str(name)]
        logger.debug('returning value for %s on %s', name, invocation)
        invocation.return_value(variant)


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
                 iface_template=IFACE_TEMPLATE,
                 *args, **kwargs):
        self.registered = False
        self._workers = dict()

        logger.debug("registering producer on name: %s, %s", name, dbus_name)

        super(Producer, self).__init__(name=name, *args, **kwargs)
        try:
            self._dbus = dbus_instances[dbus_name]
        except KeyError:
            self._dbus = dbus_instances[dbus_name] = DbusInstance(dbus_name, iface_template)

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

        self.registred = self._dbus.register_path_for_name(self.name, self._on_interest)
        if not self.registred: self.emit('register-failed', self.registered)

    def send(self, name, data, flags = {}):
        logger.debug('producer: sending on name %s, %s', name, data)
        self._dbus.return_value(name, GLib.Variant('(ss)', (str(name), data)))

    def sendFinish(self, data):
        self._dbus.return_value(name, GLib.Variant('(ss)', (str(self.name), data)))

    def _on_interest(self, name):
        logger.debug('producer: got interest for name %s, %s', name, self)
        self.emit('interest', name, Interest(name), None, None, None)

if __name__ == '__main__':
    import argparse
    from ..tests import utils as testutils
    from ... import utils

    loop = GLib.MainLoop()

    def dump(*a):
        print a

    def on_complete(i, *a):
        del(consumers[consumers.index(i)])
        len(consumers) or loop.quit()


    parser = argparse.ArgumentParser()
    args = utils.parse_args(parser=parser)
    producers = [Producer('/endlessm/%s'%(i)) for i in range(10)]
    consumers = [Consumer('/endlessm/%s'%(i)) for i in range(3)]
    [p.start() for p in producers]
    [p.connect('interest', lambda i, n, *a: p.send(n, n)) for p in producers]
    [c.start() for c in consumers]
    [c.connect('complete', on_complete) for c in consumers]

    loop.run()
