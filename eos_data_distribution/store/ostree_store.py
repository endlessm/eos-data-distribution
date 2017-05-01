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

import gi

from gi.repository import GObject
from gi.repository import GLib

from eos_data_distribution import names, subscription, utils
from eos_data_distribution.store import simple_store


def main():
    import sys
    import argparse
    from tempfile import mkdtemp

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--store-dir", required=True)

    args = utils.parse_args(parser=parser, include_name=False)

    subscription_producer = subscription.Producer(args.store_dir)
    subscription_producer.start()

    store = simple_store.Producer(
        base=args.store_dir, prefix=names.SUBSCRIPTIONS_SOMA)
    store.start()
    GLib.MainLoop().run()


if __name__ == '__main__':
    main()
