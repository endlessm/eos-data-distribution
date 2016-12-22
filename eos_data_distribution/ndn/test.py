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

from . import file
from gi.repository import GLib
import re
import argparse

import logging
logging.basicConfig(level=logging.DEBUG)

def process_args(*extra):
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name")
    parser.add_argument("-o", "--output")
    [parser.add_argument(a) for a in extra]

    return parser.parse_args()

def run_test(args, name):
    loop = GLib.MainLoop()
    if args.output:
        consumer = file.FileConsumer(name, filename=args.output, auto=True)
        consumer.connect('complete', lambda  *a: loop.quit())
    loop.run()

def run_file_producer(producer_class):
    args = process_args("filename")

    if args.name:
        name = args.name
    else:
        name = args.filename

    producer = producer_class(name=name, file=args.filename, auto=True)
    run_test(args, name)

def run_url_producer(producer_class):
    args = process_args("url")

    if args.name:
        name = args.name
    else:
        name = re.sub('https?://', '', args.url)

    producer = producer_class(name=name, url=args.url, auto=True)
    run_test(args, name)

