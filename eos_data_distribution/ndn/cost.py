# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright (C) 2016 Endless Mobile INC.
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

from . import base
from pyndn.node import Node

logger = logging.getLogger(__name__)

class Producer(base.Producer):
    def __init__(self, *args, **kwargs):
        super(Producer, self).__init__(*args, **kwargs)

    def _registerPrefix(self, prefix, cost=None, controlParameters={},
                           onInterest=None, onRegisterFailed=None,
                           onRegisterSuccess=None,
                           *args, **kwargs):
        if not onInterest: onInterest = self._onInterest
        if not onRegisterFailed: onRegisterFailed = self.onRegisterFailed
        if not onRegisterSuccess: onRegisterSuccess = self.onRegisterSuccess

        if cost: controlParameters['cost'] = int(cost)
        interest = self.makeCommandInterest('/nfd/rib/register', prefix,
                                            controlParameters=controlParameters, *args, **kwargs)
        node = self.face._node
        response = Node._RegisterResponse(
            prefix, onRegisterFailed, onRegisterSuccess, node.getNextEntryId(), node,
            onInterest, self.face
        )
        self._expressInterest(interest, prefix,
                              onData=response.onData,
                              onTimeout=response.onTimeout)
        return id

if __name__ == '__main__':
    from gi.repository import GLib
    from . import base
    import argparse

    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Register with cost Test')
    parser.add_argument("name")
    parser.add_argument("-c", "--cost", default=10)
    args = parser.parse_args()

    name = args.name
    if not name:
        name = Name('/endless/test')

    producer = Producer(name)
    producer.registerPrefix(name, cost=args.cost,
                            onRegisterFailed=lambda *a: logger.info('FAILED: %s', a),
                            onRegisterSuccess=lambda *a: logger.info('SUCCESS: %s', a),
    )

    GLib.MainLoop().run()

