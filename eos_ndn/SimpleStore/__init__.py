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

from ..DirTools import Monitor
from ..Chunks import Pool

r = re.compile(r'^/+')


class Base(Pool.MixPool):
    def __init__(self, base=None, prefix='/', exts=('.shard', '.json'), split=None, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self.base = base
        self.exts = exts
        self.split = split or base
        self.prefix = prefix

        # XXX(xaiki): this is a lot of bookeeping, can probably be reduced
        self.dirs = dict()
        self.dirpubs = dict()
        self.filenames = dict()

        if base: self.publish_all_names(base)

    def _path_to_name(self, filename):
        try:
            basename = r.sub('', filename.split(self.split)[1])
        except:
            basename = filename
        return path.join(self.prefix.toUri(), basename)

    def unpublish(self, basedir):
        [self.unpublish_name(n) for n in self.dirpubs[basedir]]
        del self.dirpubs[basedir]
        del self.dirs[basedir]

    def _unpublish_name(self, M, p, m, f, o, evt, e=None, d=None):
        return self.unpublish_name(f, d)

    def unpublish_name(self, name, basedir=None):
        print 'remove', name
        self.remove_producer(name)
        filename = self.filenames[name]
        del self.filenames[name]

        if basedir:
            del self.dirpubs[basedir][n]

    def _publish_name(self, M, p, m, f, o, evt, e=None, d=None):
        return self.publish_name(f, d)

    def publish_name(self, filename, basedir=None):
        print 'publish', filename, self.prefix
        if not filename.endswith(self.exts):
            print('ignoring', filename, self.exts)
            return

        name = self._path_to_name(filename)
        producer = self.add_producer(name, filename)
        self.filenames[name] = filename
        if basedir:
            try:
                self.dirpubs[basedir].update({name: producer})
            except KeyError:
                self.dirpubs[basedir] = {name: producer}

    def walk_dir(self, basedir):
        for root, dirs, files in walk(basedir):
            # for dir in dirs:
            #     self.walk_dir(path.join(root,dir))
            for file in files:
                print 'publish-name', basedir, file
                self.publish_name(path.join(root, file), basedir)

    def publish_all_names(self, basedir):
        self.walk_dir(basedir)
        monitor = Monitor(basedir)
        [monitor.connect(s, self._publish_name, basedir) for s in monitor.filterSignals(['created', 'moved-in', 'renamed'])]
        [monitor.connect(s, self._unpublish_name, basedir) for s in monitor.filterSignals(['moved-out', 'renamed'])]
        self.dirs[basedir] = monitor


class Producer(Base):
    def __init__(self, *args, **kwargs):
        super(Producer, self).__init__(*args, **kwargs)


class Consumer(Base):
    def __init__(self, *args, **kwargs):
        super(Consumer, self).__init__(*args, **kwargs)
