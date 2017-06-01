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
from .. import defaults, utils
from ..names import Name

logger = logging.getLogger(__name__)


# the manifest producer is an http Producer that answers on a different name
class Producer(http.Producer):

    def __init__(self, name, url, session=None, *args, **kwargs):
        getter = http.Getter(
            url, onData=self._send_finish, session=session)
        self._last_modified = http.get_last_modified(getter._headers)
        if not self._last_modified:
            raise ValueError("Could not get Last-Modified")

        # XXX -- we mangle the name in the constructor, this is slow
        name = Name(str(name) + '%ver%' + self._last_modified)

        super(Producer, self).__init__(
            name, url, getter=getter, *args, **kwargs)

    def _get_final_segment(self):
        return self._getter._size // self.chunk_size

    def _send_finish(self, data):
        data.setMetaInfo({'freshnessPeriod': defaults.FRESHNESS_PERIOD})

        self.sendFinish(data)

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

    producer = Producer(name=name, url=args.url)
    testutils.run_producer_test(producer, name, args)
