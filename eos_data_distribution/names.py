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

import re

# from pyndn import Name
# we replace this with a hack for this rewrite

class Name(list):
    def __init__(self, name):
        super(Name, self).__init__()
        if isinstance(name, str):
            self.append(name)
        else:
            self.extend(name)

    def append(self, subname):
        subname = re.sub(r'^\/+', '', subname)
        subname = re.sub(r'\/+$', '', subname)
        self.extend(subname.split('/'))
        return self

    def appendSegment(self, segment):
        return self.append(str(segment))

    def size(self):
        return len(self)

    def getSubName(self, size):
        return Name(self[size:])

    def get(self, e):
        return self[e]

    def __repr__(self):
        return '/' + '/'.join(self)

# Why isn't our name com.endlessm ?

# while com.endlessm is a valid name, it doesn't make sense semantically,
# as 'com.endlessm' represents 2 levels of naming and hence should be
# /com/endlessm/.
# but as we have no knowledge of how /com will be handled we can't really
# use that.
# strictly speaking and semantically, it would make more sense to use
# /endless-ndn/ (compared to /ndn/ used by the testbed).
# but /endlessm will do, and can be linked later on to /com/endlessm
# once a /com authority exists.


SUBSCRIPTIONS_BASE = Name('/endlessm/subscriptions/')
SUBSCRIPTIONS_INSTALLED = Name(SUBSCRIPTIONS_BASE).append('/installed')
SUBSCRIPTIONS_SOMA = Name(SUBSCRIPTIONS_BASE).append('/soma')
