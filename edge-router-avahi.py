#!/usr/bin/python
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

import gi

from gi.repository import GLib
#from gi.repository import Gio

from MDNS import ServiceDiscovery
import netifaces

from Chunks import Producer

SERVICES = ["_nfd._tcp", "_nfd._udp"]

gatways, ips = None, None

def flatten(l):
    return [i for s in l for i in s]

class EdgeRouter(Producer):
    def __init__(self):
        sda = ServiceDiscovery(SERVICES)
        sda.start()

        sda.connect('service-added', self.service_added_cb)
        sda.connect('service-removed', self.service_removed_cb)

        self.sda = sda
        self.ips = []
        self.gateways = []

        self.routed(False)

    def routed(self, routed):
        self._routed = routed
        if routed:
            print "Not Being routed by an NDN node, acting as an edge router"
            self.stop()
            return

        print "Being routed by an NDN node at %s, NOT acting as an edge router" % (self._routed)
        self.start()

    def stop(self):
        print "Not implemented"

    def start(self):
        print "Not implemented"

    def refresh_network(self):
        self.gateways = netifaces.gateways()
        self.ips = flatten(
            map(lambda a: [x['addr'] for x in a],
                [flatten(netifaces.ifaddresses(i).values())
                 for i in netifaces.interfaces()]))

    def service_added_cb(self, sda, interface, protocol, name, type, h_type, domain, host, aprotocol, address, port, txt, flags):
        self.refresh_network()

        if address in self.ips:
            print "%s is my address, skipping" % address
            return

        ifname = sda.siocgifname(interface)
        print "Found Service data for service '%s' of type '%s' (%s) in domain '%s' on %s.%i:" % (name, h_type, type, domain, ifname, protocol)

        self.routed(ifname)

    def service_removed_cb(self, sda, interface, protocol, name, type, domain, flags):
        print "Disappeared Service '%s' of type '%s' in domain '%s' on %s.%i." % (name, type, domain, sda.siocgifname(interface), protocol)

    def network_changed_cb(monitor, available):
        print "network changed"
        gatways = netifaces.gateways()

if __name__ == "__main__":
#    nm = Gio.NetworkMonitor.get_default()
#    nm.connect('network-changed', network_changed_cb)
    er = EdgeRouter()
    
    loop = GLib.MainLoop()
    loop.run()
