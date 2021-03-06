#!/usr/bin/env python2
import sys

from setuptools import setup, find_packages

PYTHON_MAJOR_MINOR = '%s.%s' % (sys.version_info[0], sys.version_info[1])

# m2crypto 0.25 broke compatability with py2.4
if PYTHON_MAJOR_MINOR > '2.4':
    M2CRYPTO_REQUIRES = 'm2crypto'
else:
    M2CRYPTO_REQUIRES = 'm2crypto<0.24'

setup(
    name='pulp-client-lib',
    version='2.22a1',
    license='GPLv2+',
    packages=find_packages(exclude=['test']),
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    install_requires=['isodate>0.5.0', 'okaara>=1.0.32,<1.0.36', 'setuptools', M2CRYPTO_REQUIRES]
)
