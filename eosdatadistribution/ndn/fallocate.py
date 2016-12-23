
import ctypes
import ctypes.util

FALLOC_FL_KEEP_SIZE = 0x01

def _fallocate():
    libc_name = ctypes.util.find_library('c')
    libc = ctypes.CDLL(libc_name)

    raw_fallocate = libc.fallocate
    raw_fallocate.restype = ctypes.c_int
    raw_fallocate.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int64, ctypes.c_int64]

    def fallocate(fd, offs, size, mode=FALLOC_FL_KEEP_SIZE):
        ret = raw_fallocate(fd, mode, offs, size)
        if ret != 0:
            raise IOError(ctypes.get_errno ())

    return fallocate

fallocate = _fallocate()
del _fallocate
