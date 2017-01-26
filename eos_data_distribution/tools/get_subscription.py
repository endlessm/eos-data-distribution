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

import argparse
import itertools
import json
import os
import re
import sys

import gi
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')

from gi.repository import GLib
from gi.repository import Gio

from eos_data_distribution.defaults import ENDLESS_NDN_CACHE_PATH
from eos_data_distribution.subscription import Fetcher
from eos_data_distribution.parallel import Batch
from eos_data_distribution.tools import util


def get_subscription_ids_for_arg(arg):
    # Check if it's an app ID.
    for data_dir in GLib.get_system_data_dirs():
        subscriptions_path = os.path.join(
            data_dir, 'ekn', arg, 'subscriptions.json')
        if os.path.exists(subscriptions_path):
            subscriptions_json = json.load(open(subscriptions_path, 'r'))
            return [subscription_entry['id'] for subscription_entry in subscription_json['subscriptions']]

    # Otherwise, assume it's a subscription ID.
    return [arg]


def mount_get_root(mount):
    drive = mount.get_drive()
    if not drive or not drive.is_removable():
        return None
    root = mount.get_root()

    print "found drive", drive.get_name()
    return os.path.join(root.get_path(), ENDLESS_NDN_CACHE_PATH)


def get_default_store_dir():
    monitor = Gio.VolumeMonitor.get()
    usb_stores = [m for m in [mount_get_root(mount)
                              for mount in monitor.get_mounts()] if m]
    if usb_stores:
        return usb_stores[0]
    else:
        return "./eos_subscription_data"


def main():
    parser = argparse.ArgumentParser(
        description="Download content for a number of subscription IDs or app IDs")
    parser.add_argument(
        "-t", "--store-dir", default=get_default_store_dir(), help="where to store the downloaded files")
    parser.add_argument("ids", nargs='+')

    args = util.process_args(parser)

    subscription_ids = list(itertools.chain.from_iterable(
        (get_subscription_ids_for_arg(arg) for arg in args.ids)))
    assert len(subscription_ids)

    loop = GLib.MainLoop()

    fetchers = [Fetcher(args.store_dir, subscription_id)
                for subscription_id in subscription_ids]

    batch = Batch(fetchers, "Subscriptions")
    batch.connect('complete', lambda *a: loop.quit())
    batch.start()

    loop.run()

if __name__ == '__main__':
    main()
