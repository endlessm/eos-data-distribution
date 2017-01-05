# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2016 Endless Mobile, Inc.
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
import pprint
from os import path

import gi
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')

from gi.repository import Gio
from gi.repository import GLib

from eos_data_distribution.defaults import ENDLESS_NDN_CACHE_PATH
from eos_data_distribution.names import SUBSCRIPTIONS_SOMA
from eos_data_distribution.SimpleStore import Producer as SimpleStoreProducer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_mount_interesting(mount):
    """Is the given mount interesting: does it have an associated drive,
       and does it contain NDN cache data?"""
    return (mount.get_drive() and
            path.exists(path.join(mount.get_root().get_path(),
                                  ENDLESS_NDN_CACHE_PATH)))


def mount_added_cb(monitor, mount, store):
    if not is_mount_interesting(mount):
        return logger.warning("No NDN data found on %s (%s)",
                              mount.get_name(), mount.get_uuid() or "no UUID")

    drive = mount.get_drive()
    root = mount.get_root()
    base = path.join(root.get_path(), ENDLESS_NDN_CACHE_PATH)

    logger.info("Starting import from %s (%s)",
                drive.get_name(), drive.get_identifier() or "no identifier")
    store.publish_all_names(base)


def mount_removed_cb(monitor, mount, store):
    root = mount.get_root()
    root_path = root.get_path()
    pprint.pprint([store.remove_name(n) for p, n in store.producers.items() if p.startswith(root_path)])


def main():
    loop = GLib.MainLoop()
    monitor = Gio.VolumeMonitor.get()
    store = SimpleStoreProducer(prefix=SUBSCRIPTIONS_SOMA, split=ENDLESS_NDN_CACHE_PATH)

    for mount in monitor.get_mounts():
        mount_added_cb(monitor, mount, store)
    monitor.connect("mount-added", mount_added_cb, store)
    monitor.connect("mount-removed", mount_removed_cb, store)
    loop.run()


if __name__ == '__main__':
    main()
