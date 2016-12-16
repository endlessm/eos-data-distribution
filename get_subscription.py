import logging
import argparse

from gi.repository import GLib

from eos_data_distribution.subscription import Fetcher
from eos_data_distribution.parallel import Batch
from eos_data_distribution.ndn.base import GLibUnixFace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

loop = GLib.MainLoop()
face = GLibUnixFace()

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--store-dir", default="./eos_subscription_data")
parser.add_argument("appids", nargs='+')

args = parser.parse_args()

fetchers = [Fetcher(args.store_dir, s, face=face).start() for s in args.appids]
batch = Batch(fetchers, "Subscriptions")
batch.connect('complete', lambda *a: loop.quit())

loop.run()


