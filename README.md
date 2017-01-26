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
   Names are hierchical in a DNS-like fashion, e.g. in `/foocorp/alice/my_data.txt/v1`
   `/foocorp` owns `/foocorp/alice` that owns `/foocorp/alice/my_data.txt`...
   
 * **Producer** - A program that knows how to provide a data packet for a name
   within its scope. It should register a prefix with the NFD, e.g. /foocorp/,
   and returns or delegates incoming *interests*, returning data packets.

 * **Interest** - A request for a data packet. In the most basic case, is just
   the name of the data packet. They can have [flags](https://named-data.net/doc/ndn-tlv/interest.html)
   attached to them. You should note that an Interest describes a 'need' for data,
   the actual data forfilling that need may come from another Name, that said the
   Interest's Name **has to** be a prefix of the Data Name. i.e. `/foocorp/alice/my_data.txt/v1`
   can be satisfied by a Data Packet on the Name `/foocorp/alice/my_data.txt/v1/checksum=a79b50d27902aa11111059c73de6ca42a3938bb8/date=8866d56af3f56f4e3b3acac8996e82dddf9c28e6/chunk0`
 
 * **Command Interest** - The Routing Deamon (NFD) can be configured at runtime,
   routes, strategies, filters, and much more can be altered via the 
   [Management API](https://redmine.named-data.net/projects/nfd/wiki/Management)
   that is activated by sending special kinds of Signed Interests called Command Interests.

 * **Consumer** - A program that requests a named data packet using an *interest*.

 * **NFD** - The Name Forwarding Daemon. A piece of software on the client
   machine that is aware of all producers and consumers and pairs the two up
   based on what it believes is the best route.
   
 * **Named Data** - Data is said to be named when there is a direct, unalterable mapping
   between a chunk of data and a name. NDN Data packets have that property, you **cannot**
   have 2 different data packets with the same name (or very bad things will occur). This
   concept is important, because sets of named data are easily mapped to NDN Packets, other
   sets (like random files on HTTP) must first be translated into an inmutable naming scheme.

 * **Chunk** - Since NDN packets are limited in size, approaches are taken to
   split larger files up into small data packets. A standard approach is called
   "chunking", where files are chunked into N-sized packets, and each
   data packet has a suffix clarifying its place in the sequence. NDN has
   standard naming conventions for this approach.

 * **Face** - A connection to the NFD program. Effectively an API around a
   UNIX socket, WebSocket, TCP, UDP or anything that establishes a connection with 
   NFD (even ethernet, there is in fact a libpcap based transport). In NDN terms a face can
   be (without distinctions) another router (another NFD) or an application. Through the Face
   API you can register prefixes, send data and express interests, among other things.

 * **EDD** - Acronym for ‘EOS Data Distribution’, the name of the project.

## Coding style and NDN API references

This package follows [PEP 8](https://www.python.org/dev/peps/pep-0008/).

There are various references for the NDN API. This project follows the
[Common Client Libraries API](http://named-data.net/doc/ndn-ccl-api/) where
possible. It also follows the
[PyNDN API](http://named-data.net/doc/0.4.0/PyNDN2/pyndn.html); and the
[NDN naming conventions](http://named-data.net/doc/tech-memos/naming-conventions.pdf)
where possible.

## License

This package is licensed under the LGPLv3+.
