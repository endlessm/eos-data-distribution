AM_CPPFLAGS = $(BOOST_CPPFLAGS) $(NDN_CPPFLAGS)
AM_LDFLAGS = $(BOOST_LDFLAGS) $(NDN_LDFLAGS)

bin_PROGRAMS = edd-ostree-store
edd_ostree_store_SOURCES = store.cpp store.hpp
edd_ostree_store_LDADD = $(BOOST_SYSTEM_LIB) $(NDN_LIBS)
