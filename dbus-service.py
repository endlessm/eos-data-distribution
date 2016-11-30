# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2014-2016 Regents of the University of California.
# Author: Jeff Thompson <jefft0@remap.ucla.edu>
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
from pyndn import Face

from NDN import Consumer, Endless

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

from os import path
import json

IFACE = '''<node>
<interface name='com.endlessm.EknSubscriptionsDownloader'>
<method name='DownloadSubscription'>
    <arg type='s' direction='in' name='subscription_id' />
</method>
</interface>
</node>'''

IFACE_INFO = Gio.DBusNodeInfo.new_for_xml(IFACE).interfaces[0]

class DBusService(object):
    def __init__(self):
        self.con = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        Gio.bus_own_name_on_connection(self.con,
                                       'com.endlessm.EknSubscriptionsDownloader',
                                       Gio.BusNameOwnerFlags.NONE,
                                       None, None)

        self.con.register_object(object_path='/com/endlessm/EknSubscriptionsDownloader',
                                 interface_info=IFACE_INFO,
                                 method_call_closure=self._on_method_call)

        # We have to fill in a name here even though we never use it...
        self._consumer = Consumer(name='dummy')

    def _on_method_call(self, connection, sender, object_path,
                        interface_name, method_name, parameters, invocation):
        # Dispatch.
        getattr(self, 'impl_%s' % (method_name, ))(invocation, parameters)

    def impl_DownloadSubscription(self, invocation, parameters):
        subscription_id, = parameters.unpack()
        name = Name(Endless.NAMES.INSTALLED).append(subscription_id)
        self._consumer.expressInterest(name, forever=True)
        invocation.return_value(None)

if __name__ == "__main__":
    service = DBusService()
    GLib.MainLoop().run()
