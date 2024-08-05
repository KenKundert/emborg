Emborg — Front-End to Borg Backup
=================================

|downloads| |build status| |coverage| |rtd status| |pypi version| |python version|

:Author: Ken Kundert
:Version: 1.40
:Released: 2024-08-05

*Emborg* is a simple command line utility to orchestrate backups. It is built as 
a front-end to Borg, a powerful and fast deduplicating backup program.  With 
*Emborg*, you specify all the details about your backups once in advance, and 
then use a very simple command line interface for your day-to-day activities.  

Use of *Emborg* does not preclude the use of Borg directly on the same 
repository.  The philosophy of *Emborg* is to provide commands that you would 
use often and in an interactive manner with the expectation that you would use 
Borg directly for the remaining commands.


Getting Help
------------

You can find the documentation on `ReadTheDocs <https://emborg.readthedocs.io>`_.

The *help* command provides information on how to use Avendesora's various
features.  To get a listing of the topics available, use::

    emborg help

Then, for information on a specific topic use::

    emborg help <topic>

It is worth browsing all of the available topics at least once to get a sense of
all that *Emborg* can do.


.. |downloads| image:: https://pepy.tech/badge/emborg/month
    :target: https://pepy.tech/project/emborg

..  |build status| image:: https://github.com/KenKundert/emborg/actions/workflows/build.yaml/badge.svg
    :target: https://github.com/KenKundert/emborg/actions/workflows/build.yaml

.. |coverage| image:: https://coveralls.io/repos/github/KenKundert/emborg/badge.svg?branch=master
    :target: https://coveralls.io/github/KenKundert/emborg?branch=master

.. |rtd status| image:: https://img.shields.io/readthedocs/emborg.svg
   :target: https://emborg.readthedocs.io/en/latest/?badge=latest

.. |pypi version| image:: https://img.shields.io/pypi/v/emborg.svg
    :target: https://pypi.python.org/pypi/emborg

.. |python version| image:: https://img.shields.io/pypi/pyversions/emborg.svg
    :target: https://pypi.python.org/pypi/emborg/

