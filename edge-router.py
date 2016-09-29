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
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')

from gi.repository import Gio
from gi.repository import GLib

from zeroconf import *
import socket
import time

class ServiceListener(object):
    def __init__(self, r = Zeroconf()):
        self.r = r

    def removeService(self, zeroconf, type, name):
        print
        print "Service", name, "removed"

    def addService(self, zeroconf, type, name):
        print
        print "Service", name, "added"
        print "  Type is", type
        info = self.r.getServiceInfo(type, name)
        if info:
            print "  Address is %s:%d" % (socket.inet_ntoa(info.getAddress()),
                                          info.getPort())
            print "  Weight is %d, Priority is %d" % (info.getWeight(),
                                                      info.getPriority())
            print "  Server is", info.getServer()
            prop = info.getProperties()
            if prop:
                print "  Properties are"
                for key, value in prop.items():
                    print "    %s: %s" % (key, value)

if __name__ == '__main__':
    r = Zeroconf()
    type = "_dynamix._tcp.local."
    browser = ServiceBrowser(r, type, listener= ServiceListener(r))
    # Search for devices for 40 seconds. 
    time.sleep(40)
    r.close()
