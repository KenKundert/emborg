Emborg — Front-End to Borg Backup
==================================

.. image:: https://img.shields.io/pypi/v/emborg.svg
    :target: https://pypi.python.org/pypi/emborg

.. image:: https://img.shields.io/pypi/pyversions/emborg.svg
    :target: https://pypi.python.org/pypi/emborg/

:Author: Ken Kundert
:Version: 1.12.0
:Released: 2019-12-25

*Emborg* is a simple command line utility to orchestrate backups. It is built as 
a front-end to Borg, a powerful and fast deduplicating backup program.  With 
*Emborg*, you specify all the details about your backups once in advance, and 
then use a very simple command line interface for your day-to-day activities.  
The details are contained in ~/.config/emborg.  That directory contains a file 
(settings) that contains shared settings, and then another file for each backup 
configuration you have.

Use of *Emborg* does not preclude the use of Borg directly on the same 
repository.  The philosophy of *Emborg* is to provide commands that you would 
use often and in an interactive manner with the expectation that you would use 
Borg directly for the remaining commands.

An alternative to *Emborg* is
`Borgmatic <https://github.com/witten/borgmatic>`_.  It seems largely focused on 
the archive creation process and offers little for the other management tasks 
such as monitoring (*due*, *list*, *manifest*), restoration (*extract*, *restore*,
*mount*), and maintenance (*check*, *prune*). *borgmatic* recently added support 
for the Borg extract command.


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
