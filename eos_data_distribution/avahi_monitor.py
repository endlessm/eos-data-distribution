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
import netifaces

logging.basicConfig(level=logging.INFO)

from subprocess import check_call

from pyndn.control_parameters import ControlParameters

from eos_data_distribution import defaults
from eos_data_distribution.ndn import base
from eos_data_distribution.names import SUBSCRIPTIONS_SOMA
from eos_data_distribution.MDNS import ServiceDiscovery


MAX_PEERS = 5  # wild guess
MIN_PEERS = 2  # minimum redundancy

SERVICES = [
    # Disable TCP, we really only want UDP or ethernet
    # "_nfd._tcp",
    "_nfd._udp"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def flatten(l):
    list(itertools.chain.from_iterable(l))


def face_uri_from_triplet(type, host, port):
    if type == '_nfd._udp':
        proto = 'udp4'
    else:
        proto = 'tcp4'
    return "%s://%s:%s" % (proto, host, port)


def build_registry_key(name, type, domain):
    return "%s-%s-%s" % (name, type, domain)


class AvahiMonitor(object):

    """
    Listen for _nfd.* on avahi, when we see a new server (a new NFD) we add
    a static link to it using nfdc
    """

    def __init__(self):
        """
        Attributes:
            gateways (dict): Dictionary containing the network gateways
                for this machine, as a mapping from address family to a
                list of ``(address, interface, is_default)`` tuples.
            _ndn_gateways (dict): Dictionary containing the addresses for
                network gateways which advertise as NDN nodes, as a mapping
                from key (see ``build_registry_key()``) to IP address.
            _registry (dict): Dictionary containing all known NDN nodes
                advertised over Avahi, as a mapping from key
                (see ``build_registry_key()``) to face URI
                (see ``face_uri_from_triplet()``).
            _routed (bool): `True` if one of the gateways for this machine
                is an NDN node; `False` otherwise.
        """
        super(AvahiMonitor, self).__init__()

        self.ips = []
        self.gateways = []
        self._peers = set()
        self._ndn_gateways = dict()
        self._registry = dict()

        self._routed = False

        sda = ServiceDiscovery(SERVICES)

        sda.connect('service-added', self.service_added_cb)
        sda.connect('service-removed', self.service_removed_cb)

        sda.start()
        self.sda = sda

        """
        self.ndn = base.Base(name=SUBSCRIPTIONS_SOMA)
        cp = ControlParameters()
        cp.setStrategy('/localhost/nfd/strategy/multicast')
        # XXX: check that we could set-strategy
        self.ndn.expressCommandInterest(
            '/nfd/strategy-choice/set', controlParameters=cp)
        """

        # XXX: Use the above native code for this.
        self.check_call(
            ["nfdc", "set-strategy", str(SUBSCRIPTIONS_SOMA), 'ndn:/localhost/nfd/strategy/multicast'])

        self._routed = False
        self.update_routes()

    def update_routes(self):
        prev_routed = self._routed
        self._routed = set(
            self._ndn_gateways.values()).intersection(self.gateways)
        self.process_route_changes(prev_routed)

    def process_route_changes(self, prev_routed):
        """ adds/removes hops for route state changes:
        - !routed -> routed  : remove all peers but gateways
        - routed  -> !routed : add MAX_PEERS peers, remove gateways
        - !routed -> !routed : check we still have enough peers (MIN_PEERS)
        - routed  -> routed  : do nothing (handled in the rest of the code)

        :param prev_routed: previous routed state
        :returns: None
        :rtype: NoneType
        """
        if not self._routed:
            if prev_routed:
                logger.info(
                    "NOT Being routed by an NDN node, disabling NDN connnections")
                self._ndn_gateways.keys().map(self.remove_nexthop)
            # we are not routed, we need to wait until we are to do anything
            return

        logger.info(
            "Being routed by an NDN node, NOT acting as an edge router")
        if not prev_routed:
            # need to remove old links...
            self._registry.values().map(self.remove_nexthop)
            # ..and only add one to the routers
            self._ndn_gateways.keys().map(self.add_nexthop)
            # ..and stop edge
            self.stop_edge()
        else:
            # no change: i am routed, i was routed before: no links
            pass

    def service_added_cb(self, sda, interface, protocol, name, type, h_type, domain, host, aprotocol, address, port, txt, flags):
        logger.debug(
            "Found Service data for service '%s' of type '%s' (%s) in domain '%s'",
                     name, h_type, type, domain)

        self.refresh_network()

        if address in self.ips:
            return

        faceUri = face_uri_from_triplet(type, host, port)
        key = build_registry_key(name, type, domain)
        self._registry[key] = faceUri

        if address in self.gateways:
            self._ndn_gateways[key] = address

        self.update_routes()

    def service_removed_cb(self, sda, interface, protocol, name, type, domain, flags):
        logger.debug(
            "Disappeared Service '%s' of type '%s' in domain '%s'",
            name, type, domain)

        self.refresh_network()

        key = build_registry_key(name, type, domain)
        try:
            del self._ndn_gateways[key]
        except KeyError:
            pass

        faceUri = self._registry[key]
        if self.remove_nexthop(faceUri)
        del self._registry[key]

        prev_routed = self._routed
        self.update_routes()

    def add_nexthop(self, faceUri):
        if len(self._peers) > MAX_PEERS:
            logger.debug(
                "refusing to add %s as we'd go over %d peers", faceUri, MAX_PEERS)
            return

        if self.check_call(["nfdc", "add-nexthop",
                            "-c", str(defaults.RouteCost.LOCAL_NETWORK),
                            str(SUBSCRIPTIONS_SOMA), faceUri]):
            self._peers.add(faceUri)

    def remove_nexthop(self, faceUri):
        try:
            self._peers.remove(faceUri)
            self.check_call(["nfdc", "remove-nexthop",
                             str(SUBSCRIPTIONS_SOMA), faceUri])
        except KeyError:
            pass

    def start_edge(self):
        return self.check_call(["systemctl", "start", "edd-soma-subscriptions-producer"])

    def stop_edge(self):
        return self.check_call(["systemctl", "stop", "edd-soma-subscriptions-producer"])

    def get_gateways(self):
        gateways = netifaces.gateways()
        del gateways['default']
        return [g[0] for g in flatten(gateways.values())]

    def refresh_network(self, *args, **kwargs):
        self.gateways = self.get_gateways()
        self.ips = flatten(
            map(lambda a: [x['addr'] for x in a], [flatten(netifaces.ifaddresses(i).values()) for i in netifaces.interfaces()]))

    def check_call(self, a):
        try:
            check_call(a)
            return True
        except CalledProcessError as e:
            logger.warning("Error calling: %s : %s", a, e)
            return False


def main():
    from gi.repository import GLib

    monitor = AvahiMonitor()

    loop = GLib.MainLoop()
    loop.run()


if __name__ == "__main__":
    main()
