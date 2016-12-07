import pytest
import time

from os import path, utime

import SimpleStore


def touch(fname, times=None):
    with open(fname, 'a'):
        utime(fname, times)


class TestClass:
    @pytest.fixture
    def callback(self):
        return 0

    def test_producer(self, tmpdir):
        d = tmpdir.mkdir("ndn")
        p = SimpleStore.Producer()
        tmpdirpath = str(d.realpath())
        tmpfilepath = path.join(tmpdirpath, 'test.shard')

        touch(tmpfilepath)

        p.publish_all_names(tmpdirpath)
        assert p.producers.keys() == [tmpfilepath]
        assert p.dirs.keys().__len__() == 1
        p.unpublish(tmpdirpath)
        assert p.producers.keys() == []
        assert p.dirs.keys().__len__() == 0
