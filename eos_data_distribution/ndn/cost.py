# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2016 Endless Mobile INC.
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

from . import base

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    from gi.repository import GLib
    from . import base
    import argparse

    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Register with cost Test')
    parser.add_argument("name")
    parser.add_argument("-c", "--cost", default=10)
    args = parser.parse_args()

    name = args.name
    if not name:
        name = Name('/endless/test')

    producer = Producer(name)
    producer.registerPrefix(name, cost=args.cost,
                            onRegisterFailed=lambda *a: logger.info('FAILED: %s', a),
                            onRegisterSuccess=lambda *a: logger.info('SUCCESS: %s', a),
    )

    GLib.MainLoop().run()

