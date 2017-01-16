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
Unit tests for ndn.file
"""


# pylint: disable=missing-docstring


from eos_data_distribution.ndn import file, chunks
from gi.repository import GObject
import logging
import os
import shutil
import tempfile
import unittest


class TestFileProducer(unittest.TestCase):
    """Test chunk retrieval from a FileProducer."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @staticmethod
    def _write_test_file(f, size):
        """Write size bytes to file f."""
        f.write('0123456789' * (size // 10))
        f.write('x' * (size % 10))

    @staticmethod
    def _n_segments_for_size(size):
        return (size + chunks.CHUNK_SIZE - 1) // chunks.CHUNK_SIZE

    def test_empty_file(self):
        """Test chunking works for an empty file."""
        path = os.path.join(self.test_dir, 'empty')
        with open(path, 'wb+') as f:
            producer = file.FileProducer('test', f)

            self.assertEqual(producer._get_final_segment(), -1)
            self.assertIsNone(producer._get_chunk(0))
            self.assertIsNone(producer._get_chunk(1))

    def test_file_sizes(self):
        """Test chunking works across files of a variety of sizes."""
        sizes = [
            chunks.CHUNK_SIZE // 10,
            chunks.CHUNK_SIZE - 1,
            chunks.CHUNK_SIZE,
            chunks.CHUNK_SIZE + 1,
            2 * chunks.CHUNK_SIZE,
            10000000,
        ]

        for size in sizes:
            logging.debug('Size: %u' % size)
            path = os.path.join(self.test_dir, 'size%u' % size)

            with open(path, 'wb+') as f:
                TestFileProducer._write_test_file(f, size)

                producer = file.FileProducer('test', f)
                n_chunks = TestFileProducer._n_segments_for_size(size)

                self.assertEqual(producer._get_final_segment(), n_chunks - 1)

                for i in range(0, n_chunks):
                    chunk = producer._get_chunk(i)
                    self.assertIsNotNone(chunk)
                self.assertIsNone(producer._get_chunk(n_chunks))


class TestSegmentTable(unittest.TestCase):
    """Test segment table functions."""

    def assertNumToBitmap(self, num, expected_bitmap):
        actual_bitmap = file.num_to_bitmap(num)
        self.assertEqual(actual_bitmap, expected_bitmap)

    def assertBitmapToNum(self, bitmap, expected_num):
        actual_num = file.bitmap_to_num(bitmap)
        self.assertEqual(actual_num, expected_num)

    def test_num_to_bitmap(self):
        self.assertNumToBitmap(0, [0, 0, 0, 0, 0, 0, 0, 0])
        self.assertNumToBitmap(1, [0, 0, 0, 0, 0, 0, 0, 1])
        self.assertNumToBitmap(2, [0, 0, 0, 0, 0, 0, 1, 0])
        self.assertNumToBitmap(19, [0, 0, 0, 1, 0, 0, 1, 1])
        self.assertNumToBitmap(255, [1, 1, 1, 1, 1, 1, 1, 1])

    def test_num_to_bitmap_invalid(self):
        with self.assertRaises(AssertionError) as e:
            file.num_to_bitmap(-1)
        with self.assertRaises(AssertionError) as e:
            file.num_to_bitmap(256)

    def test_bitmap_to_num(self):
        self.assertBitmapToNum([0, 0, 0, 0, 0, 0, 0, 0], 0)
        self.assertBitmapToNum([0, 0, 0, 0, 0, 0, 0, 1], 1)
        self.assertBitmapToNum([0, 0, 0, 0, 0, 0, 1, 0], 2)
        self.assertBitmapToNum([0, 0, 0, 1, 0, 0, 1, 1], 19)
        self.assertBitmapToNum([1, 1, 1, 1, 1, 1, 1, 1], 255)

    def test_bitmap_to_num_invalid(self):
        with self.assertRaises(AssertionError) as e:
            file.bitmap_to_num([])
        with self.assertRaises(AssertionError) as e:
            file.bitmap_to_num([0, 0, 0, 0, 0, 0, 0])
        with self.assertRaises(AssertionError) as e:
            file.bitmap_to_num([0, 0, 0, 0, 0, 0, 0, 0, 0])
        with self.assertRaises(AssertionError) as e:
            file.bitmap_to_num([0, 0, 0, 0, 0, 0, 0, 2])


if __name__ == '__main__':
    # Run test suite
    unittest.main()
