
import fcntl
import os

from . import base


def get_file_size(f):
    f.seek(0, os.SEEK_END)
    return f.tell()


class FileProducer(base.Producer):
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


class FileConsumer(base.Consumer):
    def __init__(self, name, file, *args, **kwargs):
        super(FileConsumer, self).__init__(name, *args, **kwargs)
        self.f = file
        self.fd = self.f.fileno()
        # Set the file to be non-blocking.
        flag = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)

    def _save_chunk(self, n, data):
        buf = data.getContent().toBuffer()
        start = self.chunk_size * n
        s = os.lseek(self.fd, start, os.SEEK_SET)
        return os.write(self.fd, buf)
