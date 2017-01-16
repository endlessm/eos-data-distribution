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
from os import path
import signal
import sys

import gi
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')

from gi.repository import Gio
from gi.repository import GLib

from eos_data_distribution.names import SUBSCRIPTIONS_SOMA
from eos_data_distribution.SimpleStore import Producer as SimpleStoreProducer
from eos_data_distribution import defaults

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Timeout after which this daemon will exit if no interesting mounts exist.
IDLE_TIMEOUT = 30  # seconds


def is_mount_interesting(mount):
    """Is the given mount interesting: does it contain NDN cache data?"""
    return (path.exists(path.join(mount.get_root().get_path(),
                                  defaults.ENDLESS_NDN_CACHE_PATH)))


def mount_added_cb(monitor, mount, store):
    if not is_mount_interesting(mount):
        return logger.warning("No NDN data found on %s (%s)",
                              mount.get_name(), mount.get_uuid() or "no UUID")

    root = mount.get_root()
    base = path.join(root.get_path(), defaults.ENDLESS_NDN_CACHE_PATH)

    logger.info("Starting import from %s (%s)",
                mount.get_name(), mount.get_uuid() or "no UUID")
    store.publish_all_names(base)


def mount_removed_cb(monitor, mount, store):
    root = mount.get_root()
    root_path = root.get_path()
    removed_names = [store.remove_name(n)
                     for p, n in store.dirpubs.items() if p.startswith(root_path)]
    logger.debug("Removed names: %s" % removed_names)
    maybe_time_out()


def interesting_mounts_exist():
    """Check whether any of the present mounts are interesting"""
    monitor = Gio.VolumeMonitor.get()

    for mount in monitor.get_mounts():
        if is_mount_interesting(mount):
            return True

    return False


def maybe_time_out():
    """Set up a timeout to exit the daemon if no interesting mounts exist"""
    if interesting_mounts_exist():
        return

    GLib.timeout_add_seconds(IDLE_TIMEOUT, timeout_cb)


def timeout_cb():
    if not interesting_mounts_exist():
        logger.info("Timed out as no interesting mounts exist")
        sys.exit(0)

    return GLib.SOURCE_REMOVE


def signal_cb():
    logger.info("Exiting on signal")
    sys.exit(0)


def main():
    loop = GLib.MainLoop()

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, signal_cb)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, signal_cb)
    monitor = Gio.VolumeMonitor.get()
    store = SimpleStoreProducer(prefix=SUBSCRIPTIONS_SOMA,
                                split=defaults.ENDLESS_NDN_CACHE_PATH,
                                cost=defaults.RouteCost.USB)

    for mount in monitor.get_mounts():
        mount_added_cb(monitor, mount, store)
    monitor.connect("mount-added", mount_added_cb, store)
    monitor.connect("mount-removed", mount_removed_cb, store)

    maybe_time_out()

    loop.run()


if __name__ == '__main__':
    main()
