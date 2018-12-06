#!/usr/bin/env python

from setuptools import setup

with open('README.rst') as file:
    readme = file.read()

setup(
    name = 'emborg',
    version = '0.1.0',
    author = 'Ken Kundert',
    author_email = 'emborg@nurdletech.com',
    description = 'Borg front end.',
    long_description = readme,
    download_url = 'https://github.com/kenkundert/emborg/tarball/master',
    license = 'GPLv3+',
    packages = 'emborg'.split(),
    entry_points = {'console_scripts': ['emborg=emborg.main:main']},
    install_requires = 'appdirs arrow docopt inform>=1.14 shlib>=0.8'.split(),
)
