AUTOMAKE_OPTIONS = subdir-objects
AM_CPPFLAGS = $(BOOST_CPPFLAGS) $(NDN_CPPFLAGS)
AM_LDFLAGS = $(BOOST_LDFLAGS) $(NDN_LDFLAGS)

chunksdir = $(libdir)
chunks_LTLIBRARIES =					\
	libchunks-consumer.la 				\
	libchunks-producer.la				\
	${NULL}

libchunks_consumer_la_SOURCES =				\
	core/common.hpp \
	consumer/data-fetcher.hpp \
	consumer/discover-version-fixed.hpp \
	consumer/pipeline-interests-fixed-window.cpp \
	consumer/discover-version-fixed.cpp \
	consumer/options.cpp \
	consumer/pipeline-interests-aimd.hpp \
	consumer/discover-version-iterative.hpp \
	consumer/pipeline-interests-aimd.cpp \
	consumer/pipeline-interests.cpp \
	consumer/consumer.hpp \
	consumer/consumer.cpp \
	consumer/aimd-rtt-estimator.cpp \
	consumer/options.hpp \
	consumer/discover-version.cpp \
	consumer/discover-version.hpp \
	consumer/pipeline-interests-fixed-window.hpp \
	consumer/discover-version-iterative.cpp \
	consumer/aimd-rtt-estimator.hpp \
	consumer/pipeline-interests.hpp \
	consumer/aimd-statistics-collector.cpp \
	consumer/aimd-statistics-collector.hpp \
	consumer/data-fetcher.cpp

libchunks_consumer_la_LIBADD = $(AM_LDFLAGS)

libchunks_producer_la_SOURCES =				\
	core/common.hpp \
	producer/producer.hpp \
	producer/producer.cpp

libchunks_producer_la_LIBADD = $(AM_LDFLAGS)
