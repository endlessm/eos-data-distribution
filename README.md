# eos-data-distribution

Our data distribution platform, based on [NDN](http://named-data.net/) technology.

## Why?

Offline sync is a hard problem. We want to be able to retrieve data from the
internet, from USB thumbdrives, over the local network with services like Avahi,
and in the future, maybe even functionality like mesh networking.

The Named Data project takes an interesting approach to this problem space
allowing us to send and recieve "data packets".

## The missing glossary

Here are the words you need to know:

 * **Data packet** - A data packet, in NDN terminology, is the core piece of
   data exchange in NDN. Much like BitTorrent's chunks, users exchange data
   packets which are *named*. Data packets are currently limited to 8800
   bytes, so approaches like *chunking* are required to break up larger pieces
   of data into smaller data packets.

 * **Name** - A global identifier for a specific data packet. Should include
   a version to identify the specific piece of data. If you are aware of a
   name, you can ask the "NDN network" for a data packet that maps to that name.
   Names are hierchical in a DNS-like fashion, e.g. /foocorp/alice/my_data.txt/v1

 * **Producer** - A program that knows how to provide a data packet for a name
   within its scope. It should register a prefix with the NFD, e.g. /foocorp/,
   and returns or delegates incoming *interests*, returning data packets.

 * **Interest** - A request for a data packet. In the most basic case, is just
   the name of the data packet.

 * **Consumer** - A program that requests a named data packet using an *interest*.

 * **NFD** - The Name Forwarding Daemon. A piece of software on the client
   machine that is aware of all producers and consumers and pairs the two up
   based on what it believes is the best route.

 * **Chunk** - Since NDN packets are limited in size, approaches are taken to
   split larger files up into small data packets. A standard approach is called
   "chunking", where files are chunked into N-sized packets, and each
   data packet has a suffix clarifying its place in the sequence. NDN has
   standard naming conventions for this approach.

 * **Face** - A connection to the NFD program. Effectively an API around a
   UNIX socket connection that lets you register prefixes and express
   interests, among other things.

 * **EDD** - Acronym for ‘EOS Data Distribution’, the name of the project.

## License

This package is licensed under the LGPLv3+.
