#!/usr/bin/env python

from codecs import open

from setuptools import setup

with open("README.rst", encoding="utf-8") as file:
    readme = file.read()

setup(
    name = "emborg",
    version = "1.27.0",
    author = "Ken Kundert",
    author_email = "emborg@nurdletech.com",
    description = "Borg front end.",
    long_description = readme,
    long_description_content_type = 'text/x-rst',
    url = "https://emborg.readthedocs.io",
    download_url = "https://github.com/kenkundert/emborg/tarball/master",
    license = "GPLv3+",
    packages = "emborg".split(),
    entry_points = dict(
        console_scripts = [
            "emborg=emborg.main:main",
            "emborg-overdue=emborg.overdue:main",
        ]
    ),
    install_requires = """
        appdirs
        arrow>=0.15
        docopt
        inform>=1.26
        quantiphy
        requests
        shlib>=1.0
    """.split(),
    python_requires = ">=3.6",
    zip_safe = True,
    keywords = "emborg borg borgmatic backups".split(),
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Utilities",
    ],
)
