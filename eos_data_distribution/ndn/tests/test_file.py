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
from pyndn.data import Data
from pyndn.meta_info import MetaInfo
from pyndn.name import Name
from pyndn.util.blob import Blob
import shutil
import tempfile
import unittest


class TestFileProducer(unittest.TestCase):
    """Test chunk retrieval from a FileProducer."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        print('Test directory: %s' % self.test_dir)

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


class MockFace(object):

    """
    Mock Face implementation for the purposes of testing base classes.

    This is a mock implementation of ``pyndn.face.Face`` which does no network
    communications, but looks like a ``Face`` implementation through duck
    typing.

    It records the interests expressed to it, and allows the test harness to
    reply to those interests with data (``callInterestDone()``) or a timeout
    (``callInterestTimeout()``).

    It exposes two sets of API: the public API for ``Face``, and the test
    harness API.
    """

    def __init__(self):
        # dict mapping name to (Interest, onData, onTimeout) tuple
        self._interests = {}

    # Public API to emulate Face.

    def removePendingInterest(self, name):
        raise NotImplementedError('Not implemented in MockFace yet')

    @property
    def usesGLibMainContext(self):
        return True

    def setCommandSigningInfo(self, key_chain, certificate_name):
        raise NotImplementedError('Not implemented in MockFace yet')

    def expressInterest(self, interest, on_data, on_timeout):
        self._interests[str(interest.getName())] = \
            (interest, on_data, on_timeout)
        return interest

    @property
    def isLocal(self):
        raise NotImplementedError('Not implemented in MockFace yet')
        return True

    # Test-facing API for mocking things.

    def getInterest(self, name):
        # Interests are stored as a tuple:
        # (Interest object, onDone callback, onTimeout callback)
        return self._interests[name]

    def removeInterest(self, name):
        del(self._interests[name])

    def callInterestDone(self, name, data):
        """Call the user’s onDone callback and remove the named segment."""
        (interest, on_done, _) = self.getInterest(name)
        self.removeInterest(name)
        on_done(interest, data)

    def callInterestTimeout(self, name):
        """Call the user’s onTimeout callback and remove the named segment."""
        (interest, _, on_timeout) = self.getInterest(name)
        self.removeInterest(name)
        on_timeout(interest)

    def getInterestNames(self):
        """Return names of current interests as strings."""
        return set(self._interests.keys())


class TestDirConsumer(unittest.TestCase):
    """Test file downloading using the DirConsumer class."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        print('Test directory: %s' % self.test_dir)

        # Set by _on_interest_timeout().
        self._timed_out_interest = None
        self._timed_out_try_again = False

        # Set by _on_complete().
        self._complete = False

    def tearDown(self):
        # FIXME: Ideally we would only remove the test_dir if the test was
        # successful, but that’s very hard to figure out.
        shutil.rmtree(self.test_dir)
        pass

    def assertFaceNamesEqual(self, face, names):
        """Assert the face contains interests for exactly the given names."""
        self.assertEqual(face.getInterestNames(), set(names))

    def build_paths(self, filename):
        """Build the filenames of the temporary files used by DirConsumer."""
        path = os.path.join(self.test_dir, filename)
        part_path = os.path.join(self.test_dir, filename + '.part')
        segment_path = os.path.join(self.test_dir, filename+ '.sgt')

        return (path, part_path, segment_path)

    @staticmethod
    def build_segment(name, segment_id, n_segments, segment_size=4096,
                      raw_content=None):
        """
        Build a ``pyndn.data.Data`` instance for the given segment.

        If `raw_content` is not provided, the segment will be filled with
        `segment_size` copies of the first digit of `segment_id` as an ASCII
        string.

        The final block ID is always set on the returned ``Data``.
        """
        metainfo = MetaInfo()
        metainfo.setFinalBlockId(
            Name.Component.fromNumberWithMarker(n_segments - 1, 0))

        data = Data()
        data.setName(Name(name).appendSegment(segment_id))
        if raw_content is None:
            raw_content = str(segment_id)[:1] * segment_size
        data.setContent(Blob(raw_content, False))
        data.setMetaInfo(metainfo)

        return data

    def _on_interest_timeout(self, consumer, interest, try_again):
        """Callback for Consumer.interest-timeout to capture its arguments."""
        self.assertIsNone(self._timed_out_interest)
        self._timed_out_interest = interest
        self._timed_out_try_again = try_again

    def assertInterestTimedOut(self, name):
        """
        Assert that we have received an interest-timeout signal.

        Aborts if we have not. Returns the value of try_again otherwise.

        To use this you must have connected ``_on_interest_timeout()`` to the
        ``Consumer.interest-timeout`` signal using:

            $ consumer.connect('interest-timeout', self._on_interest_timeout)
        """
        self.assertIsNotNone(self._timed_out_interest)
        self.assertEqual(str(self._timed_out_interest.getName()), name)
        try_again = self._timed_out_try_again

        self._timed_out_interest = None
        self._timed_out_try_again = False

        return try_again

    def _on_complete(self, consumer):
        """Callback for Consumer.complete to capture the state change."""
        self.assertFalse(self._complete)
        self._complete = True

    def assertFileExists(self, path):
        self.assertTrue(os.path.exists(path),
                        "File ‘%s’ does not exist when it should" % path)

    def assertNotFileExists(self, path):
        self.assertFalse(os.path.exists(path),
                         "File ‘%s’ exists when it should not" % path)

    def assertDownloadCompleted(self, filename):
        """
        Assert the download is complete for filename.

        Check that the file exists (but don’t check its contents), and that
        the part and segment files have been removed.
        """
        (path, part_path, segment_path) = self.build_paths(filename)

        self.assertFileExists(path)
        self.assertNotFileExists(part_path)
        self.assertNotFileExists(segment_path)

        # Check we received the Consumer.complete signal.
        self.assertTrue(self._complete)
        self._complete = False

    def assertDownloadNotCompleted(self, filename):
        """Opposite of assertDownloadCompleted."""
        (path, _, _) = self.build_paths(filename)

        # The final filename must not exist; but the .part and .sgt files
        # do not have to exist.
        self.assertNotFileExists(path)

        # Check we have not received the Consumer.complete signal.
        self.assertFalse(self._complete)

    def assertDownloadFailed(self, filename):
        """
        Assert the download failed for filename.

        At the moment this will fail the test, as ``Consumer`` does not have
        an error reporting path. When it gains that path, this helper should
        be updated to check that the path was followed.
        """
        (path, part_path, segment_path) = self.build_paths(filename)

        self.assertNotFileExists(path)
        self.assertNotFileExists(part_path)
        self.assertNotFileExists(segment_path)

        # Check we received the Consumer.complete signal.
        self.assertTrue(self._complete)
        self._complete = False
        self.fail('No way to report errors to the caller')

    def test_single_segment(self):
        """Test chunking works for a single segment file."""
        (path, _, _) = self.build_paths('file-name')

        # Create a new consumer requesting file-name.
        face = MockFace()
        consumer = file.DirConsumer('file-name', self.test_dir, face=face)
        consumer.connect('complete', self._on_complete)

        # Check it expresses an interest in the file.
        self.assertFaceNamesEqual(face, [])
        consumer.start()
        self.assertFaceNamesEqual(face, ['/file-name'])

        # Return the file’s only segment to the consumer.
        raw_content = 'some content'
        data = TestDirConsumer.build_segment('/file-name', 0, 1,
                                             raw_content=raw_content)

        face.callInterestDone('/file-name', data)
        self.assertFaceNamesEqual(face, [])

        # The download should have completed.
        self.assertDownloadCompleted('file-name')

        # Check the file’s contents.
        with open(path, 'r') as f:
            self.assertEqual(f.read(), raw_content)

    def test_multiple_segments(self):
        """Test chunking works for a multi-segment file."""
        (path, _, _) = self.build_paths('file-name')

        # Create a new consumer requesting file-name.
        # Set the pipeline to something massive so we don’t have to worry about
        # hitting it here. We test the pipeline in other tests.
        face = MockFace()
        segment_size=4096  # bytes
        consumer = file.DirConsumer('file-name', self.test_dir, face=face,
                                    pipeline=100, chunk_size=segment_size)
        consumer.connect('complete', self._on_complete)

        # Check it expresses an interest in the file.
        self.assertFaceNamesEqual(face, [])
        consumer.start()
        self.assertFaceNamesEqual(face, ['/file-name'])

        # Build the segments in advance.
        n_segments = 10
        segments = [TestDirConsumer.build_segment('/file-name', i, n_segments,
                                                  segment_size=segment_size)
                    for i in range(0, n_segments)]

        # Return the file’s first segment to the consumer; we expect it should
        # now express an interest in the file’s other segments.
        face.callInterestDone('/file-name', segments[0])

        remaining_segments = [
            '/file-name/%00%01',
            '/file-name/%00%02',
            '/file-name/%00%03',
            '/file-name/%00%04',
            '/file-name/%00%05',
            '/file-name/%00%06',
            '/file-name/%00%07',
            '/file-name/%00%08',
            '/file-name/%00%09',
        ]
        self.assertFaceNamesEqual(face, remaining_segments)

        # The download should not have completed yet.
        self.assertDownloadNotCompleted('file-name')

        # Return the other segments in order. We don’t expect it should
        # express any other interests.
        for i in range(1, n_segments):
            face.callInterestDone(remaining_segments[i - 1], segments[i])

        self.assertFaceNamesEqual(face, [])

        # The download should have completed.
        self.assertDownloadCompleted('file-name')

        # Check the file’s contents. It should be a n_segments * 4096-byte
        # file, with each 4096-byte chunk being its index repeated. i.e.
        # 000…111…222…
        with open(path, 'r') as f:
            for i in range(0, n_segments):
                self.assertEqual(f.read(segment_size),
                                 str(i)[:1] * segment_size)
            self.assertEqual(f.read(), '')  # EOF

    def test_single_segment_timeout(self):
        """Test chunking works for a single segment file which times out."""
        (path, _, _) = self.build_paths('file-name')

        # Create a new consumer requesting file-name.
        face = MockFace()
        consumer = file.DirConsumer('file-name', self.test_dir, face=face)
        consumer.connect('interest-timeout', self._on_interest_timeout)
        consumer.connect('complete', self._on_complete)

        # Check it expresses an interest in the file.
        self.assertFaceNamesEqual(face, [])
        consumer.start()
        self.assertFaceNamesEqual(face, ['/file-name'])

        # Time out the segment request a few times.
        for i in range(0, 10):
            face.callInterestTimeout('/file-name')
            try_again = self.assertInterestTimedOut('/file-name')
            self.assertTrue(try_again)
            self.assertFaceNamesEqual(face, ['/file-name'])

        # Now reply successfully to the request.
        raw_content = 'some content'
        data = TestDirConsumer.build_segment('/file-name', 0, 1,
                                             raw_content=raw_content)

        face.callInterestDone('/file-name', data)
        self.assertFaceNamesEqual(face, [])

        # The download should have completed.
        self.assertDownloadCompleted('file-name')

        # Check the file’s contents.
        with open(path, 'r') as f:
            self.assertEqual(f.read(), raw_content)

    def test_multiple_segments_with_timeout(self):
        """Test chunking works for a multi-segment file with a timeout."""
        (path, _, _) = self.build_paths('file-name')

        # Create a new consumer requesting file-name.
        # Set the pipeline to something massive so we don’t have to worry about
        # hitting it here. We test the pipeline in other tests.
        face = MockFace()
        segment_size=4096  # bytes
        consumer = file.DirConsumer('file-name', self.test_dir, face=face,
                                    pipeline=100, chunk_size=segment_size)
        consumer.connect('interest-timeout', self._on_interest_timeout)
        consumer.connect('complete', self._on_complete)

        # Check it expresses an interest in the file.
        self.assertFaceNamesEqual(face, [])
        consumer.start()
        self.assertFaceNamesEqual(face, ['/file-name'])

        # Build the segments in advance.
        n_segments = 4
        segments = [TestDirConsumer.build_segment('/file-name', i, n_segments,
                                                  segment_size=segment_size)
                    for i in range(0, n_segments)]

        # Return the file’s first segment to the consumer; we expect it should
        # now express an interest in the file’s other segments.
        face.callInterestDone('/file-name', segments[0])

        self.assertFaceNamesEqual(face, [
            '/file-name/%00%01',
            '/file-name/%00%02',
            '/file-name/%00%03',
        ])

        # The download should not have completed yet.
        self.assertDownloadNotCompleted('file-name')

        # Return one of the segments, then time out on one.
        face.callInterestDone('/file-name/%00%01', segments[1])
        face.callInterestTimeout('/file-name/%00%02')

        try_again = self.assertInterestTimedOut('/file-name/%00%02')
        self.assertTrue(try_again)
        self.assertFaceNamesEqual(face, [
            '/file-name/%00%02',
            '/file-name/%00%03',
        ])

        face.callInterestDone('/file-name/%00%03', segments[3])
        self.assertFaceNamesEqual(face, ['/file-name/%00%02'])

        # Time it out again, then return the data.
        face.callInterestTimeout('/file-name/%00%02')
        try_again = self.assertInterestTimedOut('/file-name/%00%02')
        self.assertTrue(try_again)
        self.assertFaceNamesEqual(face, ['/file-name/%00%02'])

        face.callInterestDone('/file-name/%00%02', segments[2])
        self.assertFaceNamesEqual(face, [])

        # The download should have completed.
        self.assertDownloadCompleted('file-name')

        # Check the file’s contents. It should be a n_segments * 4096-byte
        # file, with each 4096-byte chunk being its index repeated. i.e.
        # 000…111…222…
        with open(path, 'r') as f:
            for i in range(0, n_segments):
                self.assertEqual(f.read(segment_size),
                                 str(i)[:1] * segment_size)
            self.assertEqual(f.read(), '')  # EOF

    def test_duplicate_segments(self):
        """Test chunking correctly ignores duplicate segments for a file."""
        (path, _, _) = self.build_paths('file-name')

        # Create a new consumer requesting file-name.
        # Set the pipeline to something massive so we don’t have to worry about
        # hitting it here. We test the pipeline in other tests.
        face = MockFace()
        segment_size=4096  # bytes
        consumer = file.DirConsumer('file-name', self.test_dir, face=face,
                                    pipeline=100, chunk_size=segment_size)
        consumer.connect('complete', self._on_complete)

        # Check it expresses an interest in the file.
        self.assertFaceNamesEqual(face, [])
        consumer.start()
        self.assertFaceNamesEqual(face, ['/file-name'])

        # Build the segments in advance.
        n_segments = 10
        segments = [TestDirConsumer.build_segment('/file-name', i, n_segments,
                                                  segment_size=segment_size)
                    for i in range(0, n_segments)]

        # Return the file’s first segment to the consumer, then return the
        # other segments in order, as pairs of duplicates (i.e.
        # segment 1, segment 1, segment 2, segment 2, …).
        face.callInterestDone('/file-name', segments[0])
        for i in range(1, n_segments):
            interest_name = '/file-name/%00%0' + str(i)
            (interest, on_done, _) = face.getInterest(interest_name)
            face.removeInterest(interest_name)
            on_done(interest, segments[i])
            on_done(interest, segments[i])

        self.assertFaceNamesEqual(face, [])

        # The download should have completed.
        self.assertDownloadCompleted('file-name')

        # Check the file’s contents. It should be a n_segments * 4096-byte
        # file, with each 4096-byte chunk being its index repeated. i.e.
        # 000…111…222…
        with open(path, 'r') as f:
            for i in range(0, n_segments):
                self.assertEqual(f.read(segment_size),
                                 str(i)[:1] * segment_size)
            self.assertEqual(f.read(), '')  # EOF

    def test_multiple_segments_out_of_order(self):
        """Test chunking works for a multi-segment file out of order."""
        (path, _, _) = self.build_paths('file-name')

        # Create a new consumer requesting file-name.
        # Set the pipeline to something massive so we don’t have to worry about
        # hitting it here. We test the pipeline in other tests.
        face = MockFace()
        segment_size=4096  # bytes
        consumer = file.DirConsumer('file-name', self.test_dir, face=face,
                                    pipeline=100, chunk_size=segment_size)
        consumer.connect('complete', self._on_complete)

        # Check it expresses an interest in the file.
        self.assertFaceNamesEqual(face, [])
        consumer.start()
        self.assertFaceNamesEqual(face, ['/file-name'])

        # Build the segments in advance.
        n_segments = 10
        segments = [TestDirConsumer.build_segment('/file-name', i, n_segments,
                                                  segment_size=segment_size)
                    for i in range(0, n_segments)]

        # Return the file’s first segment to the consumer, then return the
        # other segments in reverse order (the pathological case).
        face.callInterestDone('/file-name', segments[0])
        for i in range(1, n_segments):
            # The download should not have completed yet.
            self.assertDownloadNotCompleted('file-name')

            face.callInterestDone('/file-name/%00%0' + str(i), segments[i])

        self.assertFaceNamesEqual(face, [])

        # The download should have completed.
        self.assertDownloadCompleted('file-name')

        # Check the file’s contents. It should be a n_segments * 4096-byte
        # file, with each 4096-byte chunk being its index repeated. i.e.
        # 000…111…222…
        with open(path, 'r') as f:
            for i in range(0, n_segments):
                self.assertEqual(f.read(segment_size),
                                 str(i)[:1] * segment_size)
            self.assertEqual(f.read(), '')  # EOF

# TODO: More tests:
#  - Non-requested names turning up
#  - Pipelining in chunks.Consumer
#  - NACKs: before and after receiving
#  - I/O errors: files already exist, part file exists but others don’t, etc.
#  - Locking?
#  - Corrupt segment files


if __name__ == '__main__':
    # Run test suite
    unittest.main()
