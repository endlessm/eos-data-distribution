#!/usr/bin/python
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

import gi

from gi.repository import GLib
from gi.repository import GObject

from subprocess import check_call

from pyndn.control_parameters import ControlParameters

from eos_data_distribution import defaults
from eos_data_distribution.ndn import base
from eos_data_distribution.names import SUBSCRIPTIONS_SOMA
from eos_data_distribution.MDNS import ServiceDiscovery

logging.basicConfig(level=logging.INFO)

SERVICES = [
    # Disable TCP, we really only want UDP or ethernet
    # "_nfd._tcp",
    "_nfd._udp"]


def face_uri_from_triplet(type, host, port):
    if type == '_nfd._udp':
        proto = 'udp4'
    else:
        proto = 'tcp4'
    return "%s://%s:%s" % (proto, host, port)


def build_registry_key(name, type, domain):
    return "%s-%s-%s" % (name, type, domain)


class EdgeRouter(object):

    def __init__(self):
        super(EdgeRouter, self).__init__()

        sda = ServiceDiscovery(SERVICES)

        sda.connect('service-added', self.service_added_cb)
        sda.connect('service-removed', self.service_removed_cb)

        sda.start()
        self.sda = sda
        self.ndn = base.Base(name=SUBSCRIPTIONS_SOMA)
        cp = ControlParameters()
        cp.setStrategy('/localhost/nfd/strategy/multicast')
        # XXX: check that we could set-strategy
        self.ndn.expressCommandInterest(
            '/nfd/strategy-choice/set', controlParameters=cp)
        self._registry = dict()

    def service_added_cb(self, sda, interface, protocol, name, type, h_type, domain, host, aprotocol, address, port, txt, flags):
        ifname = sda.siocgifname(interface)
        print "Found Service data for service '%s' of type '%s' (%s) in domain '%s' on %s.%i:" % (name, h_type, type, domain, ifname, protocol)
        faceUri = face_uri_from_triplet(type, host, port)
        check_call(["nfdc", "add-nexthop",
                    "-c", str(defaults.RouteCost.LOCAL_NETWORK),
                    str(SUBSCRIPTIONS_SOMA), faceUri])
        self._registry[build_registry_key(name, type, domain)] = faceUri

    def service_removed_cb(self, sda, interface, protocol, name, type, domain, flags):
        ifname = sda.siocgifname(interface)
        print "Disappeared Service '%s' of type '%s' in domain '%s' on %s.%i." % (name, type, domain, ifname, protocol)
        faceUri = self._registry[build_registry_key(name, type, domain)]
        check_call(
            ["nfdc", "remove-nexthop", str(SUBSCRIPTIONS_SOMA), faceUri])

if __name__ == "__main__":
    #    nm = Gio.NetworkMonitor.get_default()
    #    nm.connect('network-changed', network_changed_cb)
    er = EdgeRouter()

    loop = GLib.MainLoop()
    loop.run()
