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
    return DBUS_PATH_TEMPLATE % (BASE_DBUS_PATH, name.replace('-', '_'))

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

    def getName(self):
        return self

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
            interest = self.name

        self.interest = interest
        if not self.con:
            # come back when you have someone to talk too
            self._wants_start = True
            return

        dbusable_name = get_dbusable_name(interest)

        dbus_path = build_dbus_path(dbusable_name)

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
        self.IFACE_TEMPLATE = iface_template
        self.DBUS_NAME = dbus_name
        self.registered = False
        self._workers = dict()

        logger.info("name: %s, iface template: %s", name, self.IFACE_TEMPLATE)

        super(Producer, self).__init__(name=name, *args, **kwargs)
        self.con = Gio.bus_get_sync(BUS_TYPE, None)

    def _on_method_call(self, connection, sender, object_path, interface_name, method_name, parameters, invocation):
        # Dispatch.
        getattr(self, 'impl_%s' % (method_name, ))(connection, sender, object_path, interface_name, method_name, parameters, invocation)

    def start(self):
        self.registerPrefix()

    def registerPrefix(self, prefix=None):
        if prefix:
            # XXX: prefix registeration is handled checking that the prefix
            # is a strict subname, but 'strict' is still to be defined
            logger.error("We don't support prefix registeration")
            raise NotImplementedError()

        dbusable_name = get_dbusable_name(self.name)

        dbus_path = build_dbus_path (dbusable_name)
        iface_info= Gio.DBusNodeInfo.new_for_xml(
            self.IFACE_TEMPLATE
        ).interfaces[0]

        if self.registered:
            console.error('already registered')
            return

        Gio.bus_own_name_on_connection(
            self.con, self.DBUS_NAME, Gio.BusNameOwnerFlags.NONE, None, None)

        registered = self.con.register_object(
            object_path=dbus_path,
            interface_info=iface_info, method_call_closure=self._on_method_call)

        if not registered:
            logger.error('got error: %s, %s, %s, %s',
                         registered, self.DBUS_NAME, dbus_path,
                         self.IFACE_TEMPLATE)
            self.emit('register-failed', registered)

        logger.info('registred: %s, %s, %s',
                    self.DBUS_NAME, dbus_path, self.IFACE_TEMPLATE)

        self.registered = True

    def send(self, name, data, flags = {}):
        self.invocation.return_value(GLib.Variant('(ss)', (str(name), data)))

    def sendFinish(self, data):
        self.invocation.return_value(GLib.Variant('(ss)', (str(self.name), data)))

    def impl_RequestInterest(self, connection, sender, object_path, interface_name, method_name, parameters, invocation):
        logger.debug('GOT RequestInterest')
        name, = parameters.unpack()
        self.invocation = invocation
        self.emit('interest', name, Interest(name), None, None, None)
