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

from pyndn.control_parameters import ControlParameters
from pyndn.encoding.tlv_wire_format import TlvWireFormat
from pyndn.util.command_interest_generator import CommandInterestGenerator
from pyndn import Interest, Name

logger = logging.getLogger(__name__)

_commandInterestGenerator = CommandInterestGenerator()

def makeCommandInterest (*args, **kwargs):
    logger.debug("args kwargs: %s %s", args, kwargs)
    _commandInterestGenerator.generate(*args, **kwargs)

controlMap = {
    'name': 'setName',
    'faceid': 'setFaceId',
    'uri' : 'setUri',
    'control': 'setLocalControlFeature',
    'origin': 'setOrigin',
    'cost': 'setCost',
    'flags': 'setFlags',
    'mask': 'setMask',
    'strategy': 'setStrategy',
    'expiration': 'setExpirationPeriod',
    'persistency': 'setFacePersistency',
    'flagbit': 'setFlagBit'
}

def makeInterest(cmd, flags=None, local=True,
                 keyChain=None, certificateName=None,
                 controlParameters={}):
    cp = ControlParameters()

    logger.debug('control Parameters: %s', controlParameters)
    for c in controlParameters:
        getattr(cp,controlMap[c])(controlParameters[c])

    assert(cmd.startswith('/'))

    commandInterest = Interest()
    if local:
        commandInterest.setName(Name("/localhost%s" % cmd))
        # The interest is answered by the local host, so set a short timeout.
        commandInterest.setInterestLifetimeMilliseconds(2000.0)
    else:
        commandInterest.setName(Name("/localhop%s" % cmd))
        # The host is remote, so set a longer timeout.
        commandInterest.setInteresLifetimeMilliseconds(4000.0)
    # NFD only accepts TlvWireFormat packets.
    commandInterest.getName().append(cp.wireEncode(TlvWireFormat.get()))
    makeCommandInterest(commandInterest,
                        keyChain, certificateName,
                        TlvWireFormat.get())

    return commandInterest

if __name__ == '__main__':
    from gi.repository import GLib
    from . import base
    import argparse

    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Command Interest Tests')
    parser.add_argument("-n", "--name")
    parser.add_argument("command")

    args = parser.parse_args()
    name = args.name
    if not name:
        name = Name('/endless/test')

    args = parser.parse_args()
    consumer = base.Consumer(name)
    interest = consumer.makeCommandInterest(args.command, name)
    consumer._expressInterest(interest)
    consumer.connect('data', lambda *a: logger.info(a))
    consumer.connect('interest-timeout', lambda *a: logger.info(a))

    GLib.MainLoop().run()
