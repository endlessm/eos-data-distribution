# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2016 Endless Mobile, Inc.
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

from collections import defaultdict
from os import path, walk
import logging

from ..DirTools import Monitor
from ..ndn.file import FileProducer
from ..names import Name

logger = logging.getLogger(__name__)


class Producer(object):

    def __init__(self, base, prefix='/',
                 exts=('.shard', '.json'), cost=None):
        assert base
        self.base = path.realpath(base)
        self.exts = exts
        self.prefix = prefix
        self.cost = cost

        # XXX(xaiki): this is a lot of bookeeping, can probably be reduced
        self.dirs = dict()
        self.dirpubs = defaultdict(lambda: {})

    def start (self):
        self.publish_all_names(self.base)

    def _path_to_name(self, filename):
        assert filename.startswith(self.base)
        file_path = filename[len(self.base):].lstrip('/')
        return Name('%s/%s' % (str(self.prefix), file_path))

    def unpublish(self, basedir):
        [self.unpublish_name(n) for n in self.dirpubs[basedir]]
        del self.dirpubs[basedir]
        del self.dirs[basedir]

    def _unpublish_name(self, M, p, m, f, o, evt, e=None, d=None):
        return self.unpublish_name(f, d)

    def unpublish_name(self, name, basedir):
        key = str(name)
        producer = self.dirpubs[basedir][key]
        producer.removeRegisteredPrefix(name)
        del self.dirpubs[basedir][key]

    def _publish_name(self, M, p, m, f, o, evt, e=None, d=None):
        return self.publish_name(f.get_path(), d)

    def publish_name(self, filename, basedir):
        if not filename.endswith(self.exts):
            return

        name = self._path_to_name(filename)
        file = open(filename, 'rb')
        producer = FileProducer(name, file, cost=self.cost)
        producer.start()
        self.dirpubs[basedir].update({str(name): producer})

    def walk_dir(self, basedir):
        for root, dirs, files in walk(basedir):
            # for dir in dirs:
            #     self.walk_dir(path.join(root,dir))
            for file in files:
                self.publish_name(path.join(root, file), basedir)

    def publish_all_names(self, basedir):
        self.walk_dir(basedir)
        monitor = Monitor(basedir)
        [monitor.connect(s, self._publish_name, basedir)
         for s in monitor.filterSignals(['created', 'moved-in', 'renamed'])]
        [monitor.connect(s, self._unpublish_name, basedir)
         for s in monitor.filterSignals(['moved-out', 'renamed'])]
        self.dirs[basedir] = monitor

if __name__ == '__main__':
    import argparse
    from .. import utils
    from gi.repository import GLib

    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("-p", "--prefix", default='/')
    args = utils.parse_args(parser=parser, include_name=False)

    loop = GLib.MainLoop()

    producer = Producer(base=args.directory, prefix=args.prefix)
    producer.start()

    loop.run()
