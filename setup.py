#!/usr/bin/env python

from setuptools import setup

with open('README.rst') as file:
    readme = file.read()

setup(
    name = 'emborg',
    version = '1.3.0',
    author = 'Ken Kundert',
    author_email = 'emborg@nurdletech.com',
    description = 'Borg front end.',
    long_description = readme,
    url = 'https://github.com/kenkundert/emborg',
    download_url = 'https://github.com/kenkundert/emborg/tarball/master',
    license = 'GPLv3+',
    packages = 'emborg'.split(),
    entry_points = {'console_scripts': ['emborg=emborg.main:main']},
    install_requires = 'appdirs arrow docopt inform>=1.15 shlib>=1.0'.split(),

    keywords='emborg borg borgify backups'.split(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Utilities',
    ],
)
