from gi.repository import Gio
from gi.repository import GObject

EventToSignal = {Gio.FileMonitorEvent.__dict__[i]: i.lower().replace('_', '-')
                 for i in Gio.FileMonitorEvent.__dict__ if not i.startswith('__')}


class Monitor(GObject.GObject):
    __gsignals__ = {v: (GObject.SIGNAL_RUN_FIRST, None, (str, object, object, object, object, object))
                    for k, v in EventToSignal.items()}

    def __init__(self, dir, flags=Gio.FileMonitorFlags.NONE, userdata=None):
        GObject.GObject.__init__(self)
        self.userdata = userdata
        self.flags = flags
        self.monitors = dict()
        f = Gio.file_new_for_path(dir)
        if not self.isDir(f):
            raise ValueError(
                'Asked to monitor something that is not a dir: %s' % (dir, ))
        self.monitorAll(f)

    # XXX: this is needed because older version of Gio.Monitor implement
    # different signals.
    def filterSignals(self, a):
        return [e for e in a if e in EventToSignal.keys()]

    def monitorAll(self, f):
        if not self.monitor(f):
            return
        for i in f.enumerate_children("", Gio.FileQueryInfoFlags.NONE, None):
            self.monitorAll(f.get_child(i.get_name()))

    def isDir(self, f):
        return f.query_file_type(Gio.FileQueryInfoFlags.NONE) == Gio.FileType.DIRECTORY

    def monitor(self, f):
        if not self.isDir(f):
            return None
        try:
            return self.monitors[f.get_path()]
        except:
            pass

        m = Gio.File.monitor_directory(f, self.flags, None)
        m.connect('changed', self.changed_cb, self.userdata)
        self.monitors[f.get_path()] = m

    def changed_cb(self, m, f, o, evt, d):
        p = f.get_path()
        self.emit(EventToSignal[evt], p, m, f, o, evt, d)

        try:
            if self.isDir(f):
                if self.monitors[p]:
                    self.monitors[p].cancel()
        except:
            pass

        if o:
            f = o
        return self.monitorAll(f)


if __name__ == '__main__':

    def cb_changed(M, p, m, f, o, evt, d=None, e=None):
        print('signal', e, p, f, o, evt)

    from gi.repository import GLib
    m = Monitor('./tmp')
    [m.connect(s, cb_changed, s) for s in EventToSignal.values()]

    GLib.MainLoop().run()
