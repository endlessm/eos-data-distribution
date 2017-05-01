from ..dbus import base
from ... import defaults, utils

TEST_NAME = '/endlessm/test'

def _on_data(consumer, interest, response):
    print("GOT DATA: %s", response)

def _on_interest(producer, prefix, interest, *args):
    print("Sending back")
    producer.send(interest, "ALL DONE", flags={'freshnessPeriod': defaults.FRESHNESS_PERIOD})

if __name__ == '__main__':
    from gi.repository import GLib

    args = utils.parse_args()

    consumer = base.Consumer(TEST_NAME)
    consumer.connect('data', _on_data)

    producer = base.Producer(TEST_NAME)
    producer.connect('interest', _on_interest)

    consumer.start()
    producer.start()

    GLib.MainLoop().run()
