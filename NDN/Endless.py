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

# THIS FILE CONTAINS ENDLESS DEFAULTS

import logging
from os import path
from pyndn import Name

LOGLEVEL = logging.INFO
BASE = '/endless/'

try:
    import gi

    gi.require_version('Notify', '0.7')
    from gi.repository import Notify
    Notify.init ("NDN")
except:
    Notify = False

class Names(dict):
    __getattr__= dict.__getitem__
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

    def __init__(self, *args, **kwargs):
        super(Names, self).__init__(*args, **kwargs)

NAMES = Names ({k: Name (path.join(BASE, v)) for k,v in {
    'BASE': '',
    'INSTALLED': 'installed',
    'SOMA':  'soma/v1'
}.items()})

SOMA_SUB_BASE = 'https://subscriptions.prod-blue.soma.endless-cloud.com/v1'
# SOMA_SUB_BASE = 'https://subscriptions.prod.soma.endless-cloud.com'

def notify_log (log, title, subtitle=None, notification=None):
    log ("notify: %s, %s"%(title, subtitle))
    if not Notify:
        return None

    if notification:
        notification.update (title, subtitle)
    else:
        notification = Notify.Notification.new(title, subtitle)

    notification.show()
    return notification
