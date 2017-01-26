#!/usr/bin/python
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

from gi.repository import GLib
import argparse

import logging
logger = logging.getLogger(__name__)


class ArgParseWrapper(object):

    """
    all this because we can't call parse_args twice...
    """

    def __init__(self, *args, **kwargs):
        self.parser = argparse.ArgumentParser(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        self.parser.add_argument(*args, **kwargs)

    def parse_args(self, *args, **kwargs):
        args = self.parser.parse_args()
        if args.v == 0:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.DEBUG)
        return args


def process_args(description=None, *args, **kwargs):
    parser = ArgParseWrapper(description)
    parser.add_argument("-n", "--name")
    parser.add_argument("-v", action="count")

    return parser


def run_producer_test(producer, name, args):
    loop = GLib.MainLoop()

    producer.start()
    if args.output:
        from .. import file
        consumer = file.FileConsumer(name, filename=args.output)
        consumer.connect('complete', lambda *a: loop.quit())
        consumer.start()
    loop.run()
