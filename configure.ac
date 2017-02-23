#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.69])

m4_define([as_major_version], [0])
m4_define([as_minor_version], [1])
m4_define([as_micro_version], [0])
m4_define([as_version],
          [as_major_version.as_minor_version.as_micro_version])

AC_INIT([eos-data-distribution], [as_version], [https://endlesm.com])
AC_CONFIG_MACRO_DIR([m4])

AS_MAJOR_VERSION=as_major_version
AS_MINOR_VERSION=as_minor_version
AS_MICRO_VERSION=as_micro_version
AS_VERSION=as_version
AC_SUBST(AS_MAJOR_VERSION)
AC_SUBST(AS_MINOR_VERSION)
AC_SUBST(AS_MICRO_VERSION)
AC_SUBST(AS_VERSION)

# enable nice build output on automake1.11
m4_ifdef([AM_SILENT_RULES],[AM_SILENT_RULES([no])])

AX_BOOST_BASE([1.48],, [AC_MSG_ERROR([eos-data-distribution needs Boost, but it was not found on your system])])
AX_BOOST_SYSTEM
AX_BOOST_FILESYSTEM

AC_PROG_CXX

PKG_CHECK_MODULES(NDN, libndn-cxx >= 0.5.0)

AM_INIT_AUTOMAKE
AC_CONFIG_FILES([Makefile src/Makefile])
AC_OUTPUT
