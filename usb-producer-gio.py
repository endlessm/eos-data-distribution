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

from os import path, walk
from Chunks import Producer

from pyndn import Face

ENDLESS_NDN_CACHE_PATH = ".endless-NDN-DATA"
ENDLESS_NDN_BASE_NAME = "/endless/soma/v0/"

def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

class ProducerPool(object):
    def __init__(self, chunkSize=4096):
        self.pool = dict()
        self.face = Face()

        GLib.timeout_add(100, lambda: self.face.processEvents())

    def publish_name(self, filename):
        name = path.join(ENDLESS_NDN_BASE_NAME,
                            filename.split(ENDLESS_NDN_CACHE_PATH)[1])
        producer = Producer (name, filename, face=self.face)
        producer.registerPrefix()
        self.pool[name] = producer

    def publish_all_names(self, base):
        for root, dirs, files in walk(base):
            for file in files:
                if file.endswith(".shard"):
                    print(path.join(root, file))
                    self.publish_name(path.join(root, file))

def mount_added_cb(monitor, mount, pool):
    drive = mount.get_drive()
    root = mount.get_root()
    base = path.join(root.get_path(), ENDLESS_NDN_CACHE_PATH)

    if drive:
        dump(drive.get_name())

    if path.exists(base):
        print ("Starting import")
        pool.publish_all_names(base)
    else:
        print ("No NDN data found !")

if __name__ == '__main__':
    loop = GLib.MainLoop()
    monitor = Gio.VolumeMonitor.get()
    pool = ProducerPool()

    for mount in monitor.get_mounts():
        mount_added_cb(monitor, mount, pool)
    monitor.connect("mount-added", mount_added_cb, pool)
    loop.run()
