
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
        return self._file_size // self.chunk_size

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
        os.makedirs(dirname)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(dirname):
            pass
        else:
            raise


# The segment table is a really simple format to describe a partially
# downloaded file. Each .sgt file has a simple magic of 8 bytes:
#
# 8 bytes magic - "EosSgtV1"
#
# The segment map has:
# 8 bytes - num_segments, the number of segments in the file.
#
# After that is a bitmap containing num_segments bits. Read the bitmap
# as if you converted it into a large string of bits, with the MSB of
# the first byte at the 0th index, and the LSB of the last bit at the
# last index. If num_segments is not cleanly divisible by 8, any
# remaining bits in the bitmap are undefined and can be ignored.
#
# If the Nth index in the file is set, it means that the corresponding
# segment has completed downloading and has been written into the file.

SEGMENT_TABLE_MAGIC = 'EosSgtV1'

# 7 => [0, 0, 0, 0, 0, 1, 1, 1]
def num_to_bitmap(n):
    assert 0 <= n <= 255
    return [int(c) for c in list(bin(n)[2:].zfill(8))]

# [0, 0, 0, 0, 0, 1, 1, 1] -> 7
def bitmap_to_num(bitmap):
    assert len(bitmap) == 8
    n = 0
    for idx, bit in enumerate(bitmap[::-1]):
        n |= bit << idx
    return n

class FileConsumer(chunks.Consumer):
    def __init__(self, name, filename, *args, **kwargs):
        self._filename = filename
        mkdir_p(os.path.dirname(self._filename))

        self._part_filename = '%s.part' % (self._filename, )
        self._part_fd = os.open(self._part_filename, os.O_CREAT | os.O_WRONLY | os.O_NONBLOCK)
        self._sgt_filename = '%s.sgt' % (self._filename, )
        self._sgt_fd = os.open(self._sgt_filename, os.O_CREAT | os.O_RDWR)

        super(FileConsumer, self).__init__(name, *args, **kwargs)

    # XXX: This is disgusting hackery. We need to remove auto=True.
    def consume(self):
        # If we have an existing download to resume, use that. Otherwise,
        # request the first segment to bootstrap us.
        try:
            self._read_segment_table()
        except ValueError as e:
            pass

        if self._segments is not None:
            self._schedule_interests()
        else:
            self._request_segment(0)

    def _save_chunk(self, n, data):
        buf = data.getContent().toBytes()
        offs = self.chunk_size * n
        os.lseek(self._part_fd, offs, os.SEEK_SET)
        os.write(self._part_fd, buf)
        self._write_segment_table()

    def _set_final_segment(self, n):
        super(FileConsumer, self)._set_final_segment(n)

        # Reserve space for the full file...
        fallocate.fallocate(self._part_fd, 0, self._size)

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

        # If there's no magic, then the file is busted, and we have no state to update.
        if magic != SEGMENT_TABLE_MAGIC:
            return

        # Flags -- reserved for now.
        flags = read8()

        # Num segments.
        num_segments = read8()
        completed_segments = []

        for i in xrange(0, num_segments, 8):
            byte = ord(os.read(self._sgt_fd, 1))
            completed_segments += num_to_bitmap(byte)

        segments = completed_segments[:num_segments]
        self._segments = [SegmentState.COMPLETE if bit else SegmentState.UNSENT for bit in segments]

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
        write8(0)

        write8(len(self._segments))

        for i in xrange(0, len(self._segments), 8):
            segments = self._segments[i:i+8]
            bitmap = [1 if state == SegmentState.COMPLETE else 0 for state in segments]
            bitmap = (bitmap + [0] * 8)[:8]
            byte = bitmap_to_num(bitmap)
            os.write(self._sgt_fd, chr(byte))

    def _on_complete(self):
        os.close(self._part_fd)
        os.close(self._sgt_fd)
        os.rename(self._part_filename, self._filename)
        os.unlink(self._sgt_filename)
        super(FileConsumer, self)._on_complete()
