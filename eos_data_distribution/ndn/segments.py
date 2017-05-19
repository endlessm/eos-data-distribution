# -*- coding: utf-8 -*-
import logging
import struct
import fcntl
import os

from io import BytesIO

from ..defaults import SegmentState

logger = logging.getLogger(__name__)

# The segment table is a really simple format to describe a partially
# downloaded file. Each .sgt file has a simple magic of 8 bytes:
# All integer values are little-endian.
#
# 8 bytes magic - "EosSgtV1"
# 1 byte "mode".
# 7 bytes flags - reserved
#
# The most basic mode is mode 0 -- "basic segment table":
#   8 bytes - num_segments, the number of segments in the file.
#
#   After that is a bitmap containing num_segments bits. Read the bitmap
#   as if you converted it into a large string of bits, with the MSB of
#   the first byte at the 0th index, and the LSB of the last bit at the
#   last index. If num_segments is not cleanly divisible by 8, any
#   remaining bits in the bitmap are undefined and can be ignored.
#
#   If the Nth index in the file is set, it means that the corresponding
#   segment has completed downloading and has been written into the file.
#
# Mode 1 is a basic kind of compression for when the basic segment table
# is too big: hole-compressed segmented table.
#
#   8 bytes -- num_segments, the number of segments in the file.
#   8 bytes -- num_completed_segments
#   8 bytes -- num_holes
#   For each hole: 8 bytes -- hole_index
#
#   To construct a segment table from the segment table, construct a table
#   num_segments long. Mark all indexes lower than num_completed_segments
#   as being complete. Then, mark each segment for at each hole_index as
#   incomplete.

SEGMENT_TABLE_MAGIC = 'EosSgtV1'

def dump_segments(segments):
    import operator

    cm = "_o#"
    s = ''
    step = len(segments)/64
    for i in xrange(0, (len(segments)), step):
        a = segments[i:i+step]
        c = int(float(reduce(operator.add, a))/step)
        s = s + cm[c]

    return s

def num_to_bitmap(n):
    """7 => [0, 0, 0, 0, 0, 1, 1, 1]"""
    assert 0 <= n <= 255
    return [int(c) for c in list(bin(n)[2:].zfill(8))]


def bitmap_to_num(bitmap):
    """[0, 0, 0, 0, 0, 1, 1, 1] -> 7"""
    assert len(bitmap) == 8
    n = 0
    for bit in bitmap:
        assert bit in [0, 1]
        n = (n << 1) | bit
    return n

class File:
    def __init__(self, filename, mode=0):
        self.mode = mode
        self._filename = '%s.sgt' % (filename, )
        self._fd = os.open(
            self._filename, os.O_CREAT | os.O_RDWR, 0o600)

        # Before doing any I/O on the files, check we can get a lock on the
        # segment file.
        try:
            self.lock()
        except IOError as e:
            self.close()
            raise e

    def unlock(self):
        return fcntl.flock(self._fd, fcntl.LOCK_UN)

    def lock(self):
        fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def close(self, unlink=False):
        try:
            self.unlock()
        except IOError as e:
            pass

        os.close(self._fd)
        self._fd = -1

        if unlink:
            os.unlink(self._filename)
        self._filename = None

    def read(self):
        def read8():
            try:
                return struct.unpack('<Q', os.read(self._fd, 8))[0]
            except struct.error:
                logger.debug("COULDNT READ SEGMENT TABLE, unpack")
                raise ValueError()

        try:
            os.lseek(self._fd, 0, os.SEEK_SET)
            magic = os.read(self._fd, len(SEGMENT_TABLE_MAGIC))
        except OSError as e:
            logger.debug("COULDNT READ SEGMENT TABLE, magic")
            raise ValueError()

        # If there's no magic, then the file is busted, and we have no state to
        # update.
        if magic != SEGMENT_TABLE_MAGIC:
            logger.debug("COULDNT READ SEGMENT TABLE, magic: %s", magic)
            raise ValueError()

        # Flags -- reserved for now.
        flags = read8()

        mode = flags & 0xFF

        def read_mode0():
            # Num segments.
            num_segments = read8()
            completed_segments = []

            for i in range(0, num_segments, 8):
                byte = ord(os.read(self._fd, 1))
                completed_segments += num_to_bitmap(byte)

            segments = completed_segments[:num_segments]
            return [
                SegmentState.COMPLETE if bit else SegmentState.UNSENT for bit in segments]

        def read_mode1():
            num_segments = read8()
            num_complete_segments = read8()
            num_unsent_segments = num_segments - num_complete_segments
            segments = ([SegmentState.COMPLETE] * num_complete_segments) + (
                [SegmentState.UNSENT] * num_unsent_segments)

            num_holes = read8()
            for i in range(num_holes):
                hole_index = read8()
                segments[hole_index] = SegmentState.UNSENT

            return segments

        logger.debug ('reading mode %s', mode)
        read = [read_mode0, read_mode1]
        return read[mode]()

    def write(self, segments):
        # If we don't have any segment state yet, just quit.
        if segments is None:
            return

        bio = BytesIO(b"")

        def write8(value):
            return bio.write(struct.pack('<Q', value))

        def write1(value):
            return bio.write(struct.pack('<B', value))

        bio.write(SEGMENT_TABLE_MAGIC)

        # Flags.
        mode = self.mode
        flags = 0 | mode

        write8(mode)
        write8(len(segments))

        def write_mode0(segments):
            for i in xrange(0, len(segments), 8):
                section = segments[i:i + 8]
                bitmap = [
                    1 if state == SegmentState.COMPLETE else 0 for state in section]
                bitmap = (bitmap + [0] * 8)[:8]
                byte = bitmap_to_num(bitmap)
                logger.debug('write %s -> %s', i, byte)
                write1(byte)


        def write_mode1(segments):
            try:
                first_unsent_index = segments.index(SegmentState.UNSENT)
            except ValueError as e:
                first_unsent_index = len(segments)

            unsent_segments = segments[first_unsent_index:]
            # Make sure there are no complete and outgoing segments past the
            # first unsent one...
            assert unsent_segments.count(SegmentState.COMPLETE) == 0
            assert unsent_segments.count(SegmentState.OUTGOING) == 0

            # All complete segments are before this index.
            num_complete_segments = first_unsent_index
            write8(num_complete_segments)

            complete_segments = segments[:num_complete_segments]
            hole_indexes = [i for i, state in enumerate(
                complete_segments) if state == SegmentState.OUTGOING]
            write8(len(hole_indexes))
            for hole_index in hole_indexes:
                write8(hole_index)

        [write_mode0, write_mode1][mode](segments)

        bio.seek(0)
        # Truncate the file so it contains nothing.
        os.ftruncate(self._fd, 0)
        os.lseek(self._fd, 0, os.SEEK_SET)
        os.write(self._fd, bio.read())

if __name__ == '__main__':
    import argparse
    from .. import utils

    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mode", default=0, type=int)

    args = utils.parse_args(parser=parser, include_name=False)

    segments =      [SegmentState.COMPLETE]*500
    segments.extend([SegmentState.OUTGOING]*500)
    segments.extend([SegmentState.UNSENT]*500)


    s = File('test-segments', mode=args.mode)
    s.write(segments)
    s.close()

    logger.debug('segments: (%s) %s', len(segments), dump_segments(segments))

    s = File('test-segments')
    segments = s.read()
    logger.debug('segments: (%s) %s', len(segments), dump_segments(segments))

