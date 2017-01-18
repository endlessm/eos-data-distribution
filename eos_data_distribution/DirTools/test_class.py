import pytest
from eos_data_distribution import DirTools

from gi.repository import GLib

ITER_COUNT = 10


class TestClass:

    @pytest.mark.timeout(timeout=3, method='thread')
    def test_0(self, tmpdir):
        loop = GLib.MainLoop()
        self.__called = 0

        def cb_changed(M, p, m, f, o, evt, d=None, e=None):
            print('signal', e, p, f, o, evt, d)
            assert e == 'created'
            self.__called += 1

        d = tmpdir.mkdir("ndn")
        m = DirTools.Monitor(str(d))
        [m.connect(s, cb_changed, s) for s in ['created']]
        [d.mkdir(str(i)) for i in range(ITER_COUNT)]

        GLib.timeout_add_seconds(2, lambda: loop.quit())
        loop.run()
        assert self.__called == ITER_COUNT
