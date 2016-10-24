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

from os import path, walk
from pyndn import Face
from Chunks import Pool

class Producer(Pool):
    def __init__(self, base, *args, **kwargs):
        super(Producer, self).__init__(*args, **kwargs)
        self.base = base

        if not base:
            import sys
            sys.exit()

    def publish_name(self, filename, split):
        name = path.join(self.base,
                         filename.split(split)[1])
        self.addProducer(name, filename)

    def publish_all_names(self, basedir, split):
        for root, dirs, files in walk(basedir):
            for file in files:
                if file.endswith(".shard"):
                    print(path.join(root, file))
                    self.publish_name(path.join(root, file), split)
