#!/usr/bin/env python

from codecs import open

from setuptools import setup

with open("README.rst", encoding="utf-8") as file:
    readme = file.read()

setup(
    name="emborg",
    version="1.17.0",
    author="Ken Kundert",
    author_email="emborg@nurdletech.com",
    description="Borg front end.",
    long_description=readme,
    long_description_content_type='text/x-rst',
    url="https://emborg.readthedocs.io",
    download_url="https://github.com/kenkundert/emborg/tarball/master",
    license="GPLv3+",
    packages="emborg".split(),
    entry_points=dict(
        console_scripts=[
            "emborg=emborg.main:main",
            "emborg-overdue=emborg.overdue:main",
        ]
    ),
    install_requires="appdirs arrow docopt inform>=1.15 quantiphy shlib>=1.0".split(),
    python_requires=">=3.6",
    keywords="emborg borg borgmatic backups".split(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Utilities",
    ],
)
