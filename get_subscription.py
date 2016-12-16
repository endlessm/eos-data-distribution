import logging
import argparse
from os import path

import gi
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')

from gi.repository import GLib
from gi.repository import Gio

from eos_data_distribution.defaults import ENDLESS_NDN_CACHE_PATH
from eos_data_distribution.subid import APPID_TO_SUBID
from eos_data_distribution.subscription import Fetcher
from eos_data_distribution.parallel import Batch
from eos_data_distribution.ndn.base import GLibUnixFace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

loop = GLib.MainLoop()
face = GLibUnixFace()

def mount_get_root (mount):
    drive = mount.get_drive()
    root = mount.get_root()

    print "found drive", drive.get_name()
    return path.join (root.get_path(), ENDLESS_NDN_CACHE_PATH)

monitor = Gio.VolumeMonitor.get()
usb_stores = [mount_get_root(mount) for mount in monitor.get_mounts()]
try:
    store_dir = usb_stores[0]
except:
    store_dir = "./eos_subscription_data"

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--store-dir", default=store_dir)
parser.add_argument("appids", nargs='+')

args = parser.parse_args()

fetchers = [Fetcher(args.store_dir, APPID_TO_SUBID(s), face=face).start() for s in args.appids]
batch = Batch(fetchers, "Subscriptions")
batch.connect('complete', lambda *a: loop.quit())

loop.run()


