#!/usr/bin/python
# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2016 Endless Computers, Inc.
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
import logging

from . import http
from .dbus import chunks
from .. import utils

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    import re
    from .tests import utils as testutils

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cost", default=10)
    parser.add_argument("-o", "--output")
    parser.add_argument("url")
    args = utils.parse_args(parser=parser)

    if args.name:
        name = args.name
    else:
        name = re.sub('https?://', '', args.url)

    producer = http.Producer(name=name, url=args.url)
    testutils.run_producer_test(producer, name, args)
