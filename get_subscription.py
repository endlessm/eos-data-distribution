import json
import logging
import argparse
import os, sys

import gi
gi.require_version('Gio', '2.0')
gi.require_version('GLib', '2.0')

from gi.repository import GLib
from gi.repository import Gio

from eosdatadistribution.defaults import ENDLESS_NDN_CACHE_PATH
from eosdatadistribution.subscription import Fetcher
from eosdatadistribution.parallel import Batch
from eosdatadistribution.ndn.base import GLibUnixFace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app_to_sub = {}
for data_dir in GLib.get_system_data_dirs ():
    dir_path = os.path.join (data_dir, 'ekn')
    try:
        dirs = os.listdir (dir_path)
    except:
        continue

    for d in dirs:
        app_path = (os.path.join (dir_path, d))
        if not os.path.isdir (app_path):
            continue

        try:
            id = app_to_sub [d]
            continue
        except:
            print('look at', app_path)
            try:
                sub = open (os.path.join (app_path, 'subscriptions.json'))
                sub_json = json.load (sub)
                id = sub_json['subscriptions'][0]['id']
                app_to_sub[d] = id
            except:
                pass

loop = GLib.MainLoop()
face = GLibUnixFace()

def mount_get_root (mount):
    drive = mount.get_drive()
    root = mount.get_root()

    print("found drive", drive.get_name())
    return os.path.join (root.get_path(), ENDLESS_NDN_CACHE_PATH)

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

try:
    fetchers = [Fetcher(args.store_dir, app_to_sub[s], face=face).start() for s in args.appids]
except KeyError as e:
    logger.critical ("couldn't find subid for app: %s", e.args)
    sys.exit()

batch = Batch(fetchers, "Subscriptions")
batch.connect('complete', lambda *a: loop.quit())

loop.run()


