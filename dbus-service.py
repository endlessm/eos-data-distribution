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

import json
from shutil import copyfile
from os import path

from pyndn import Name
from pyndn import Face

from NDN import Consumer, Endless

import gi
gi.require_version('GLib', '2.0')

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

IFACE = '''<node>
<interface name='com.endlessm.EknSubscriptionsDownloader'>
<method name='DownloadSubscription'>
    <arg type='s' direction='in' name='subscription_id' />
</method>
</interface>
</node>'''

IFACE_INFO = Gio.DBusNodeInfo.new_for_xml(IFACE).interfaces[0]

def apply_subscription_update(subscription_id, src_manifest_path, shards):
    user_subscriptions_folder = path.expanduser('~/.local/share/com.endlessm.subscriptions/%s/' % (subscription_id, ))

    # now look at this manifest, that i just found
    with open(src_manifest_path, 'r') as f:
        manifest_obj = json.load(f)

    # Place the new shards into the zone...
    for src_shard_path in shards:
        shard_filename = path.basename(src_shard_path)
        dst_shard_path = path.join(user_subscriptions_folder, shard_filename)
        if path.exists(dst_shard_path):
            # Skip existing shards...
            continue
        copyfile(src_shard_path, dst_shard_path)

    # Place the new manifest into the zone...
    new_manifest_path = path.join(user_subscriptions_folder, 'manifest.json.new')
    copyfile(src_manifest_path, new_manifest_path)

    # Let ekn's downloader apply updates itself.

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
        self._consumer.connect('data', self._on_data)

    def _on_method_call(self, connection, sender, object_path,
                        interface_name, method_name, parameters, invocation):
        # Dispatch.
        getattr(self, 'impl_%s' % (method_name, ))(invocation, parameters)

    def _on_data(self, consumer, interest, response):
        subscription_reply = json.loads(consumer.dataToBytes(response).tobytes())

        apply_subscription_update(subscription_reply['subscription_id'],
                                  subscription_reply['manifest_path'],
                                  subscription_reply['shards'])

    def impl_DownloadSubscription(self, invocation, parameters):
        subscription_id, = parameters.unpack()
        name = Name(Endless.NAMES.INSTALLED).append(subscription_id)
        self._consumer.expressInterest(name, forever=True)
        invocation.return_value(None)

if __name__ == "__main__":
    service = DBusService()
    GLib.MainLoop().run()
