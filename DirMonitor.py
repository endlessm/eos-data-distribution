from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject

class DirMonitor(GObject.GObject):
    __gsignals__ = {
        'changed': (GObject.SIGNAL_RUN_FIRST, None,
                    (object, object, object, object, object))
    }

    def __init__(self, dir, flags=Gio.FileMonitorFlags.NONE, userdata=None):
        GObject.GObject.__init__(self)
        self.userdata = userdata
        self.flags = flags
        self.monitors = dict()
        f = Gio.file_new_for_path(dir)
        if not self.isDir(f):
            print 'asked to monitor something that is not a dir', dir
        self.monitorAll(f)

    def monitorAll(self, f):
        if not self.monitor(f): return
        for i in f.enumerate_children("", Gio.FileQueryInfoFlags.NONE, None):
            self.monitorAll(f.get_child(i.get_name()))

    def isDir(self, f):
        return f.query_file_type(Gio.FileQueryInfoFlags.NONE) == Gio.FileType.DIRECTORY

    def monitor(self, f):
        if not self.isDir(f): return None
        try:
            return self.monitors[f.get_path()]
        except:
            pass

        m = Gio.File.monitor_directory(f, self.flags, None)
        m.connect('changed', self.changed_cb, self.userdata)
        self.monitors[f.get_path()] = m

    def changed_cb(self, m, f, o, evt, d):
        self.emit('changed', m, f, o, evt, d)
        try:
            p = f.get_path()
            if not self.isDir(f) and self.monitors[p]:
                self.monitors[p].cancel()
        except:
            pass

        if o: f = o
        return self.monitorAll(f)

if __name__ == '__main__':
    def cb_changed(M, m, f, o, evt, d=None):
        print ('changed', f, o, evt)

        m = DirMonitor('./tmp')
        m.connect('changed', cb_changed)

        GLib.MainLoop().run()
