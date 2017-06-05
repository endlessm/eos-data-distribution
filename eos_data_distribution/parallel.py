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

import logging

from gi.repository import GObject

logger = logging.getLogger(__name__)


class Batch(GObject.GObject):
    __gsignals__ = {
        'complete': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, workers, type="Batch"):
        super(Batch, self).__init__()
        self._type = type
        self._incomplete_workers = set(workers)
        for worker in self._incomplete_workers:
            worker.connect('complete', self._on_batch_complete)

    def start(self):
        if not self._incomplete_workers:
            logger.info('%s complete: no workers', self._type)
            self.emit('complete')

        for worker in self._incomplete_workers:
            worker.start()

    def _on_batch_complete(self, worker):
        logger.info("%s complete: %s", self._type, worker)
        self._incomplete_workers.remove(worker)
        if len(self._incomplete_workers) == 0:
            self.emit('complete')

if __name__ == '__main__':
    import argparse
    from . import utils

    from gi.repository import GLib
    from ndn.file import FileConsumer

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output")
    parser.add_argument("-c", "--count", default=10, type=int)
    args = utils.parse_args(parser=parser)

    loop = GLib.MainLoop()

    consumers = [FileConsumer("%s-%s"%(args.name, i), "%s-%s"%(args.output, i))
                 for i in range(args.count)]
    batch = Batch(workers=consumers)
    batch.connect('complete', lambda *a: loop.quit())
    batch.start()

    loop.run()
