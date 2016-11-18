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

import sys
try:
    import avahi
    import dbus
    import avahi.ServiceTypeDatabase
    from gi.repository import GObject
except ImportError, e:
    print "A required python module is missing!\n%s" % (e)
    sys.exit()

try:
    import dbus.glib
except ImportError, e:
    pass

class ServiceTypeDatabase:
    def __init__(self):
        self.pretty_name = avahi.ServiceTypeDatabase.ServiceTypeDatabase()

    def get_human_type(self, type):
	if self.pretty_name.has_key(type):
	    return self.pretty_name[type]
        else:
            return type

class ServiceDiscovery(GObject.GObject):
    __gsignals__ = {
        'service-added': (GObject.SIGNAL_RUN_FIRST, None,
                          # interface, protocol, name, type, h_type, domain, host, aprotocol, address, port, txt, flags
                          (object, int, str, str, str, str, str, str, str, str, str, str)),
        'service-removed': (GObject.SIGNAL_RUN_FIRST, None,
                            # interface, protocol, name, type, domain, flags
                            (object, int, str,str, str, str))
        }

    def __init__(self, services = [],
                 interface = avahi.IF_UNSPEC,
                 protocol = avahi.PROTO_INET):
        GObject.GObject.__init__(self)

        self.services = services
        self.interface = interface
        self.protocol = protocol

        try:
            self.system_bus = dbus.SystemBus()
            self.system_bus.add_signal_receiver(self.avahi_dbus_connect_cb, "NameOwnerChanged", "org.freedesktop.DBus", arg0="org.freedesktop.Avahi")
        except dbus.DBusException, e:
            pprint.pprint(e)
            sys.exit(1)

        self.db = ServiceTypeDatabase()
	self.service_browsers = {}
        self.started = False

    def avahi_dbus_connect_cb(self, a, connect, disconnect):
        if connect != "":
            print "We are disconnected from avahi-daemon"
            self._stop()
        else:
            print "We are connected to avahi-daemon"
            if self.started: self._start()

    def siocgifname(self, interface):
	if interface <= 0:
	    return "any"
	else:
	    return self.server.GetNetworkInterfaceNameByIndex(interface)

    def service_resolved(self, interface, protocol, name, type, domain, host, aprotocol, address, port, txt, flags):
        h_type = self.db.get_human_type(type)
        self.emit('service-added', interface, protocol, name, type, h_type, domain, host, aprotocol, address, port, avahi.txt_array_to_string_array(txt), flags)

    def print_error(self, err):
	print "Error:", str(err)

    def service_add(self, interface, protocol, name, type, domain, flags):
	print "Found service '%s' of type '%s' in domain '%s' on %s.%i." % (name, type, domain, self.siocgifname(interface), protocol)

# this check is for local services
#        try:
#            if flags & avahi.LOOKUP_RESULT_LOCAL:
#                return
#        except dbus.DBusException:
#            pass

        self.server.ResolveService(interface, protocol, name, type, domain, avahi.PROTO_INET, dbus.UInt32(0), reply_handler=self.service_resolved, error_handler=self.print_error)

    def service_remove(self, interface, protocol, name, type, domain, flags):
        self.emit('service-removed', interface, protocol, name, type, domain, flags)
    def already_browsing(self, type):
        return self.service_browsers.has_key((self.interface,
                                              self.protocol,
                                              type,
                                              self.domain))

    def add_service_type(self, type):
        interface, protocol, domain = (self.interface, self.protocol, self.domain)
	# Are we already browsing this domain for this type? 
	if self.already_browsing(type):
	    return

	print "Browsing for services of type '%s' in domain '%s' on %s.%i ..." % (type, domain, self.siocgifname(interface), protocol)

        browser = self.server.ServiceBrowserNew(interface, protocol, type, domain, dbus.UInt32(0))
        bus = dbus.Interface(self.system_bus.get_object(avahi.DBUS_NAME, browser)

                           , avahi.DBUS_INTERFACE_SERVICE_BROWSER)
        bus.connect_to_signal('ItemNew', self.service_add)
        bus.connect_to_signal('ItemRemove', self.service_remove)

	self.service_browsers[(interface, protocol, type, domain)] = bus

    def del_service_type(self, interface, protocol, type, domain):

	service = (interface, protocol, type, domain)
	if not self.service_browsers.has_key(service):
	    return
	sb = self.service_browsers[service]
        try:
            sb.Free()
        except dbus.DBusException:
            pass
	del self.service_browsers[service]
	# delete the sub menu of service_type
	if self.zc_types.has_key(type):
	    self.service_menu.remove(self.zc_types[type].get_attach_widget())
	    del self.zc_types[type]
        if len(self.zc_types) == 0:
            self.add_no_services_menuitem()

    def start(self):
        self.started = True
        return self._start()

    def _start(self):
	try:
            self.server = dbus.Interface(self.system_bus.get_object(avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER), 
                                         avahi.DBUS_INTERFACE_SERVER)
	except:
            print "Check that the Avahi daemon is running!"
	    return

	try: 
		self.use_host_names = self.server.IsNSSSupportAvailable()
	except:
		self.use_host_names = False

        self.domain = self.server.GetDomainName()
        print "Starting discovery"

        for service in self.services:
            self.add_service_type(service)

    def stop(self):
        self.started = False
        return self._stop()

    def stop(self):
	if len(self.domain) == 0:
            print "Discovery already stopped"
	    return

        print "Discovery stopped"

