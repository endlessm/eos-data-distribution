
import errno
import fcntl
import os

from . import chunks


def get_file_size(f):
    f.seek(0, os.SEEK_END)
    return f.tell()


class FileProducer(chunks.Producer):
    def __init__(self, name, file, *args, **kwargs):
        super(FileProducer, self).__init__(name, *args, **kwargs)
        self.name = name
        self.f = file
        self._file_size = get_file_size(self.f)

    def _get_final_block_id(self):
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

class FileConsumer(chunks.Consumer):
    def __init__(self, name, filename, mode=os.O_CREAT | os.O_WRONLY, *args, **kwargs):
        super(FileConsumer, self).__init__(name, *args, **kwargs)

        self._filename = filename
        self._part_filename = '%s.part' % (self._filename, )
        mkdir_p(os.path.dirname(self._filename))
        self.fd = os.open(self._part_filename, mode | os.O_NONBLOCK)

    def _save_chunk(self, n, data):
        buf = data.getContent().toBuffer()
        start = self.chunk_size * n
        s = os.lseek(self.fd, start, os.SEEK_SET)
        return os.write(self.fd, buf)

    def _on_complete(self):
        os.close(self.fd)
        os.rename(self._part_filename, self._filename)
        super(FileConsumer, self)._on_complete()
