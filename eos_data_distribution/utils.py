# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2017 Endless Mobile, Inc.
# Author: Cosimo Cecchi <cosimo@endlessm.com>
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

def parse_args(parser=None, include_name=True):
    if parser is None:
        parser = argparse.ArgumentParser()

    if include_name:
        parser.add_argument('--name', '-n',
                            help='name of the requested interest')
    parser.add_argument('-v', action='count',
                        help='verbosity level')
    args = parser.parse_args()

    if args.v > 1:
        logging.basicConfig(level=logging.DEBUG)
    elif args.v == 1:
        logging.basicConfig(level=logging.INFO)
    else:
        # We use the default WARNING level if -v was not specified
        logging.basicConfig(level=logging.WARNING)

    return args
