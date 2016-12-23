#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2015 Collabora Ltd.
# Copyright © 2016 Endless Mobile, Inc.
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

"""
NDN producers and daemons
"""

from setuptools import setup, find_packages
import os
import version  # https://gist.github.com/pwithnall/7bc5f320b3bdf418265a


project_name = 'eos-data-distribution'
__version__ = version.get_version()
project_author = 'Endless Mobile, Inc.'
README = open('README.md').read()
NEWS = open('NEWS').read()


# From http://stackoverflow.com/a/17004263/2931197
def discover_and_run_tests():
    import os
    import sys
    import unittest

    # get setup.py directory
    setup_file = sys.modules['__main__'].__file__
    setup_dir = os.path.abspath(os.path.dirname(setup_file))

    # use the default shared TestLoader instance
    test_loader = unittest.defaultTestLoader

    # use the basic test runner that outputs to sys.stderr
    test_runner = unittest.TextTestRunner()

    # automatically discover all tests
    # NOTE: only works for python 2.7 and later
    test_suite = test_loader.discover(setup_dir)

    # run the test suite
    test_runner.run(test_suite)

try:
    from setuptools.command.test import test

    class DiscoverTest(test):

        def finalize_options(self):
            test.finalize_options(self)
            self.test_args = []
            self.test_suite = True

        def run_tests(self):
            discover_and_run_tests()

except ImportError:
    from distutils.core import Command

    class DiscoverTest(Command):
        user_options = []

        def initialize_options(self):
                pass

        def finalize_options(self):
            pass

        def run(self):
            discover_and_run_tests()


setup(
    name=project_name,
    version=__version__,
    packages=find_packages(exclude=['*.tests']),
    include_package_data=True,
    exclude_package_data={'': ['.gitignore']},
    zip_safe=True,
    setup_requires=[
        'setuptools_git >= 0.3',
    ],
    install_requires=[
        'pyndn >= 2.4b1',
    ],
    tests_require=[
        'pytest',
    ],
    entry_points={
        'console_scripts': [
            'edd-soma-subscriptions-producer = '
            'eos_data_distribution.producers.soma_subscriptions:main',
            'edd-store = eos_data_distribution.store.ostree_store:main',
            'edd-usb-producer = eos_data_distribution.producers.usb:main',
        ],
    },
    author=project_author,
    author_email='xaiki@endlessm.com',
    description=__doc__,
    long_description=README + '\n\n' + NEWS,
    license='LGPLv3+',
    url='https://github.com/endlessm/endless-ndn',
    cmdclass={'test': DiscoverTest},
)
