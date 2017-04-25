# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2017 Endless Mobile Inc.
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

from gi.repository import GObject
from ...defaults import CHUNK_SIZE, RouteCost

logger = logging.getLogger(__name__)

class Base(GObject.GObject):
    """Base class

    All this is a lie, we put here all the boilerplate code we need to have
    our clases behave like the real chunks

    """
    def __init__(self, name,
                 chunk_size=CHUNK_SIZE,
                 cost=RouteCost.DEFAULT):
        GObject.GObject.__init__(self)
        self.chunk_size = chunk_size
        self.cost = cost
        self.name = name


class Data(object):
    """Data:

    This mimics the NDN Data object, it should implement as little API as we
    need, we pass an fd that comes from the Consumer, and currently
    setContent is a hack that actually writes to the fd.
    we write here so that we don't have to cache big chunks of data in memory.

    """
    def __init__(self, fd, n = 0):
        super(Data, self).__init__()

        self.fd = fd
        self.n = n - 1

    def setContent(self, buf):
        cur_pos = self.fd.tell()
        n = self.n + 1

        assert(cur_pos/CHUNK_SIZE == n)

        # write directly to the fd, sendFinish is a NOP
        logger.debug('write data START: %d, fd: %d, buf: %d',
                     n, cur_pos, len(buf))
        ret = self.fd.write(buf)
        self.fd.flush()
        logger.debug('write data END: %d, fd: %d', n, self.fd.tell())
        self.n = n
        return ret
