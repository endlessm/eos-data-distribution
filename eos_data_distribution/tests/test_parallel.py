#!/usr/bin/python
# -*- Mode:python; coding: utf-8; c-file-style:"gnu"; indent-tabs-mode:nil -*- */
#
# Copyright © 2016 Endless Mobile, Inc.
# Author: Philip Withnall <withnall@endlessm.com>
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

"""
Unit tests for parallel
"""


# pylint: disable=missing-docstring


from eos_data_distribution import parallel
from gi.repository import GObject
import logging
import unittest


class MockOperation(GObject.GObject):
    __gsignals__ = {
        'complete': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def start(self):
        pass

    def complete(self):
        self.emit('complete')


class TestBatch(unittest.TestCase):
    """Test running operations in parallel with Batch."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    def setUp(self):
        self._complete = False

    def _complete_cb(self, batch):
        self.assertFalse(self._complete)
        self._complete = True

    def test_no_operations(self):
        batch = parallel.Batch([])
        batch.connect('complete', self._complete_cb)
        self.assertFalse(self._complete)
        batch.start()
        self.assertTrue(self._complete)

    def test_one_operation(self):
        op = MockOperation()
        batch = parallel.Batch([op])
        batch.connect('complete', self._complete_cb)
        self.assertFalse(self._complete)
        batch.start()
        self.assertFalse(self._complete)
        op.complete()
        self.assertTrue(self._complete)

    def test_two_operations(self):
        op1 = MockOperation()
        op2 = MockOperation()
        batch = parallel.Batch([op1, op2])
        batch.connect('complete', self._complete_cb)
        self.assertFalse(self._complete)
        batch.start()
        self.assertFalse(self._complete)
        op1.complete()
        self.assertFalse(self._complete)
        op2.complete()
        self.assertTrue(self._complete)

    def test_same_operation(self):
        op = MockOperation()
        batch = parallel.Batch([op, op])
        batch.connect('complete', self._complete_cb)
        self.assertFalse(self._complete)
        batch.start()
        self.assertFalse(self._complete)
        op.complete()
        self.assertTrue(self._complete)


if __name__ == '__main__':
    # Run test suite
    unittest.main()
