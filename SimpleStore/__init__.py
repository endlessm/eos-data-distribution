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

import re

from os import path, walk
from pyndn import Face
from Chunks import Pool
from DirTools import Monitor

r = re.compile(r'^/+')

class Producer(Pool):
    def __init__(self, base=None, prefix='/', ext='.shard', split=None, *args, **kwargs):
        super(Producer, self).__init__(*args, **kwargs)
        self.base = base
        self.ext = ext
        self.split = split or base
        self.prefix = prefix

        self.dirs = dict()
        self.producers = dict()

        if base:
            self.publish_all_names(base)

    def remove_name(self, name):
        self.delProducer(name)

    def publish_name(self, filename):
        print 'publish', filename, self.prefix
        if not filename.endswith(self.ext):
            print('ignoring', filename)
            return

        basename = r.sub('', filename.split(self.split)[1])
        name = path.join(self.prefix, basename)

        producer = self.addProducer(name, filename)
        self.producers[filename] = name

    def walk_dir(self, basedir):
        for root, dirs, files in walk(basedir):
            # for dir in dirs:
            #     self.walk_dir(path.join(root,dir))
            for file in files:
                print 'publish-name', basedir, file
                self.publish_name(path.join(root, file))

    def publish_all_names(self, basedir):
        self.walk_dir(basedir)
        monitor = Monitor(basedir)
        [monitor.connect(s, self.publish_name, s) for s in ['created', 'moved-in', 'renamed']]
        [monitor.connect(s, self.remove_name, s)  for s in ['moved-out', 'renamed']]
        self.dirs[basedir] = monitor
