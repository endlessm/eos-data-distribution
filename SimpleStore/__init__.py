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

from pyndn import Face

class Producer(object):
    def __init__(self, chunkSize=4096):
        self.pool = dict()
        self.face = Face()

    def publish_name(self, filename):
        name = path.join(ENDLESS_NDN_BASE_NAME,
                            filename.split(ENDLESS_NDN_CACHE_PATH)[1])
        producer = Producer (name, filename, face=self.face)
        producer.registerPrefix()
        self.pool[name] = producer

    def publish_all_names(self, base):
        for root, dirs, files in walk(base):
            for file in files:
                if file.endswith(".shard"):
                    print(path.join(root, file))
                    self.publish_name(path.join(root, file))
