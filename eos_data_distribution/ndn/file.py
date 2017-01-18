
import errno
import fcntl
import os
import struct

from . import fallocate, chunks
from .chunks import SegmentState


def get_file_size(f):
    f.seek(0, os.SEEK_END)
    return f.tell()


class FileProducer(chunks.Producer):

    def __init__(self, name, file, *args, **kwargs):
        super(FileProducer, self).__init__(name, *args, **kwargs)
        self.name = name
        self.f = file
        self._file_size = get_file_size(self.f)

    def _get_final_segment(self):
        return ((self._file_size + self.chunk_size - 1) // self.chunk_size) - 1

    def _get_chunk(self, n):
        pos = self.chunk_size * n

        if pos >= self._file_size:
            return None

        self.f.seek(pos, os.SEEK_SET)
        return self.f.read(self.chunk_size)


def mkdir_p(dirname):
    if not dirname:
        return

    try:
        os.makedirs(dirname, 0o755)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(dirname):
            pass
        else:
            raise


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


def num_to_bitmap(n):
    """7 => [0, 0, 0, 0, 0, 1, 1, 1]"""
    assert 0 <= n <= 255
    return [int(c) for c in list(bin(n)[2:].zfill(8))]


def bitmap_to_num(bitmap):
    """[0, 0, 0, 0, 0, 1, 1, 1] -> 7"""
    assert len(bitmap) == 8
    n = 0
    for idx, bit in enumerate(bitmap[::-1]):
        assert bit in [0, 1]
        n |= bit << idx
    return n


class Consumer(chunks.Consumer):

    def __init__(self, *args, **kwargs):
        super(Consumer, self).__init__(*args, **kwargs)

    # XXX: This is disgusting hackery. We need to remove auto=True.

    def start(self):
        # If we have an existing download to resume, use that. Otherwise,
        # request the first segment to bootstrap us.

        # XXX: Disable this for now, since it doesn't work with the
        # qualified name mangling we do.

        try:
            pass
            # self._read_segment_table()
        except ValueError as e:
            pass

        if self._segments is not None:
            self._schedule_interests()
        else:
            super(Consumer, self).start()

    def _save_chunk(self, n, data):
        buf = data.getContent().toBytes()
        offs = self.chunk_size * n
        os.lseek(self._part_fd, offs, os.SEEK_SET)
        os.write(self._part_fd, buf)
        self._write_segment_table()

    def _set_final_segment(self, n):
        super(Consumer, self)._set_final_segment(n)

        # Reserve space for the full file...
        try:
            fallocate.fallocate(self._part_fd, 0, self._size)
        except IOError as e:  # if it fails, we might get surprises later, but it's ok.
            pass

    def _read_segment_table(self):
        def read8():
            try:
                return struct.unpack('<Q', os.read(self._sgt_fd, 8))[0]
            except struct.error:
                raise ValueError()

        try:
            os.lseek(self._sgt_fd, 0, os.SEEK_SET)
            magic = os.read(self._sgt_fd, len(SEGMENT_TABLE_MAGIC))
        except OSError as e:
            raise ValueError()

        # If there's no magic, then the file is busted, and we have no state to
        # update.
        if magic != SEGMENT_TABLE_MAGIC:
            return

        # Flags -- reserved for now.
        flags = read8()

        mode = flags & 0xFF

        def read_mode0():
            # Num segments.
            num_segments = read8()
            completed_segments = []

            for i in range(0, num_segments, 8):
                byte = ord(os.read(self._sgt_fd, 1))
                completed_segments += num_to_bitmap(byte)

            segments = completed_segments[:num_segments]
            self._segments = [
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

            self._segments = segments

        if mode == 0:
            read_mode0()
        elif mode == 1:
            read_mode1()

    def _write_segment_table(self):
        # If we don't have any segment state yet, just quit.
        if self._segments is None:
            return

        def write8(value):
            os.write(self._sgt_fd, struct.pack('<Q', value))

        # Truncate the file so it contains nothing.
        os.ftruncate(self._sgt_fd, 0)
        os.lseek(self._sgt_fd, 0, os.SEEK_SET)
        os.write(self._sgt_fd, SEGMENT_TABLE_MAGIC)

        # Flags.
        mode = 1

        flags = 0 | mode
        write8(mode)

        def write_mode0():
            write8(len(self._segments))

            for i in range(0, len(self._segments), 8):
                segments = self._segments[i:i + 8]
                bitmap = [
                    1 if state == SegmentState.COMPLETE else 0 for state in segments]
                bitmap = (bitmap + [0] * 8)[:8]
                byte = bitmap_to_num(bitmap)

        def write_mode1():
            write8(len(self._segments))

            try:
                first_unsent_index = self._segments.index(SegmentState.UNSENT)
            except ValueError as e:
                first_unsent_index = len(self._segments)

            unsent_segments = self._segments[first_unsent_index:]
            # Make sure there are no complete and outgoing segments past the
            # first unsent one...
            assert unsent_segments.count(SegmentState.COMPLETE) == 0
            assert unsent_segments.count(SegmentState.OUTGOING) == 0

            # All complete segments are before this index.
            num_complete_segments = first_unsent_index
            write8(num_complete_segments)

            complete_segments = self._segments[:num_complete_segments]
            hole_indexes = [i for i, state in enumerate(
                complete_segments) if state == SegmentState.OUTGOING]
            write8(len(hole_indexes))
            for hole_index in hole_indexes:
                write8(hole_index)

        if mode == 0:
            write_mode0()
        elif mode == 1:
            write_mode1()

    def _on_complete(self):
        os.close(self._part_fd)
        os.close(self._sgt_fd)
        os.rename(self._part_filename, self._filename)
        os.chmod(self._filename, 0o644)
        os.unlink(self._sgt_filename)
        super(Consumer, self)._on_complete()

    def _create_files(self, filename):
        self._filename = filename
        mkdir_p(os.path.dirname(filename))
        self._part_filename = '%s.part' % (filename, )
        self._part_fd = os.open(
            self._part_filename, os.O_CREAT | os.O_WRONLY | os.O_NONBLOCK, 0o600)
        self._sgt_filename = '%s.sgt' % (filename, )
        self._sgt_fd = os.open(
            self._sgt_filename, os.O_CREAT | os.O_RDWR, 0o600)


class FileConsumer(Consumer):

    """Write to a File"""

    def __init__(self, name, filename, *args, **kwargs):
        self._create_files(filename)

        super(FileConsumer, self).__init__(name, *args, **kwargs)


class DirConsumer(Consumer):

    """Write to a Directory routing the name"""

    def __init__(self, name, dirname, *args, **kwargs):
        mkdir_p(dirname)
        self._dirname = dirname
        super(DirConsumer, self).__init__(name, *args, **kwargs)

    def _on_data(self, o, interest, data):
        self._create_files(
            os.path.join(self._dirname, chunks.get_chunkless_name(
                interest.getName())))

        super(DirConsumer, self)._on_data(o, interest, data)
        self._on_data = super(DirConsumer, self)._on_data

if __name__ == '__main__':
    from tests import util
    parser = util.process_args("filename")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    name = args.name or args.filename

    producer = Producer(name=name, file=args.filename)
    util.run_producer_test(producer, name, args)
