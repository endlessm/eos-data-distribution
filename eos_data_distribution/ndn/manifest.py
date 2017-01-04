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

import logging

from pyndn import Name

from . import http
from . import chunks

logger = logging.getLogger(__name__)
FRESHNESS_PERIOD = 1000 #ms

# the manifest producer is an http Producer that answers on a different name
class Producer(chunks.Producer):
    def __init__(self, name, url, session=None, *args, **kwargs):
        self._getter = http.Getter(url, session)
        self._getter.connect('data', lambda o, d: self._send_finish(d))

        # XXX -- we mangle the name in the constructor, this is slow
        self._qualified_name = Name(name).append(self._getter._last_modified)

        super(Producer, self).__init__(name, *args, **kwargs)

    def _get_final_segment(self):
        return self._getter._size // self.chunk_size

    def _send_chunk(self, data, n):
        qualified_name = Name(self._qualified_name).appendSegment(n)
        data.setName(qualified_name)
        self._getter.soup_get(data, n)

    def _send_finish(self, data):
        data.getMetaInfo().setFreshnessPeriod(FRESHNESS_PERIOD)

        self.sendFinish(data)

if __name__ == '__main__':
    import re
    from . import test

    args = test.process_args("url")

    if args.name:
        name = args.name
    else:
        name = re.sub('https?://', '', args.url)

    producer = Producer(name=name, url=args.url, auto=True)
    test.run_test(args, name)
