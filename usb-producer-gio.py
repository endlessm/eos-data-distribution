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
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')

from gi.repository import Gio
from gi.repository import GLib

from os import path
from Chunks import Producer

ENDLESS_NDN_CACHE_PATH = ".endless-NDN-DATA"
ENDLESS_NDN_BASE_NAME = "/endless/soma/v0/"

from SimpleStore import Producer as SimpleStoreProducer

def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

def mount_added_cb(monitor, mount, store):
    drive = mount.get_drive()
    root = mount.get_root()
    base = path.join(root.get_path(), ENDLESS_NDN_CACHE_PATH)

    if drive:
        dump(drive.get_name())

    if path.exists(base):
        print ("Starting import")
        store.publish_all_names(base, split=ENDLESS_NDN_CACHE_PATH)
    else:
        print ("No NDN data found !")

if __name__ == '__main__':
    loop = GLib.MainLoop()
    monitor = Gio.VolumeMonitor.get()
    store = SimpleStoreProducer(base=ENDLESS_NDN_BASE_NAME)

    for mount in monitor.get_mounts():
        mount_added_cb(monitor, mount, store)
    monitor.connect("mount-added", mount_added_cb, store)
    loop.run()
