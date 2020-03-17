.. Emborg documentation master file

Emborg — Front-End to Borg Backup
=================================

| Version: 1.15.2
| Released: 2020-03-17
| Please report all bugs and suggestions at
  `Github <https://github.com/KenKundert/emborg/issues>`_
  (or contact me directly at `emborg@nurdletech.com
  <mailto://emborg@nurdletech.com>`_).


What is Emborg?
---------------

*Emborg* is a simple command line utility to orchestrate backups. It is built as 
a front-end to `Borg <https://borgbackup.readthedocs.io>`_, a powerful and fast 
deduplicating backup program.  With *Emborg*, you specify all the details about 
your backups once in advance, and then use a very simple command line interface 
for your day-to-day activities.

Use of *Emborg* does not preclude the use of Borg directly on the same 
repository.  The philosophy of *Emborg* is to provide commands that you would 
use often and in an interactive manner with the expectation that you would use 
*Borg* directly for more unusual or esoteric situations.

An alternative to *Emborg* is
`borgmatic <https://github.com/witten/borgmatic>`_.  It seems largely focused on 
the archive creation process and offers little for the other management tasks 
such as monitoring (*due*, *list*, *manifest*), restoration (*mount*), and 
maintenance (*check*, *prune*).  *borgmatic* recently added support for the 
*Borg* extract command.


Why Borg?
---------

Well, everyone needs to backup their files. So perhaps the questions should be: 
why not Duplicity?  `Duplicity <http://duplicity.nongnu.org>`_ has been the 
standard way to do backups on Unix systems for many years.

*Duplicity* provides full and incremental backups. A full backup makes complete 
copies of each file. With an incremental backup, only the difference between the 
current and previous versions of the file are saved.  Thus, to retrieve a file 
from the backup, *Duplicity* must first get the original version of the file, 
and then apply each change. That approach results in the following issues:

#. The recovery process is slow because the desired file is reconstructed from 
   possibly a large number of change sets, each of which must be downloaded from 
   a remote repository before it can be applied. The change sets are large, so 
   the recovery of even small files can require downloading a large amount of 
   data.  It is common that the recovery of a single small file could require 
   many hours.

#. Because the recovery process requires so many steps, it can be fragile.  
   Apparently it keeps all the change sets open during the recovery process, and 
   so the recovery process can fail because the operating system limits how many 
   files you can open at any one time.

#. Generally, when there are problems, you only find them when you try to 
   recover a file.  At that point it is too late.

#. Duplicity does not do de-duplication, so if your were to have multiple copies 
   of the same file, or if you moved a file, then you would keep multiple copies 
   of it.

The first two issues can be reduced with frequent full backups, but this greatly 
increases the space you need to hold your backups.

*Borg* works in a very different way. When *Borg* encounters a file, it first 
determines whether it is new or not. The file is determined to be new if the 
contents of that file do not already exist in the repository, in which case it 
copies the contents into the repository.  Then, either way, it associates 
a pointer to the file's contents with the filepath.  This makes it naturally 
de-duplicating.  When it comes time to recover a file, it simply uses the file 
path to find the contents.  In this way, it only retrieves the data it needs.  
There is no complicated and fragile process needed to reconstruct the file from 
a long string of differences.

After living with Duplicity for many years, I now find the Borg recovery process 
stunningly fast and extremely reliable.  I am completely sold on Borg and will 
never use Duplicity again.


Terminology
-----------

It is helpful to understand two terms that are used used by *Borg* to describe 
your backups.

:repository:
    This is the location where all of your files are backed up to. It may be on 
    a local file system or it may be remote, in which case it is accessed using 
    *ssh*.

    A repository consists of a collection of disembodied and deduplicated file 
    contents along with a collection of archives.

:archive:
    This is a snapshot of the files that existed when a particular backup was 
    run.  Basically, it is a collection of file paths along with pointers to the 
    contents of those files.


Quick Tour
----------

You must initially describe your repository or repositories to *Emborg*.  You do 
so by adding configuration files to ~/.config/emborg. Once you have done that, 
you can use *Emborg* to perform common tasks that involve you backups.

For example::

    $ emborg init

The :ref:`init command <init>` initializes a repository, which is necessary 
before it can be used.

::

    $ emborg create

The :ref:`create command <create>` creates an archive, meaning that it backs up 
your current files.

::

    $ emborg list

The :ref:`list command <list>` displays a list of all existing archives.

::

    $ emborg manifest
    $ emborg files

The :ref:`manifest or files command <manifest>` displays all the files in the 
most recent archive.

::

    $ emborg manifest continuum-2019-04-23T18:35:33

If you give the name of an archive, it displays all the files in the specified 
archive.

::

    $ emborg diff continuum-2019-04-23T18:35:33 continuum-2019-04-22T17:24:06

The :ref:`diff command <diff>` shows you the difference between two archives.

::

    $ emborg extract home/seven/bin/vu

The :ref:`extract command <extract>` extracts a file or directory from the most 
recent archive.

::

    $ cd ~/bin
    $ emborg restore vu

The :ref:`restore command <restore>` restores files or directories in place, 
meaning it replaces the current version with the one from the archive.

::

    $ emborg mount BACKUPS

The :ref:`mount command <mount>` creates a directory 'BACKUPS' and then mounts 
an archive or the whold repository on this directory.  This allows you to move 
into the archive or repository, navigating, examining, and retrieving files as 
if it were a file system.

::

    $ emborg umount BACKUPS

The :ref:`umount command <umount>` un-mounts the archive or repository after you 
are done with it.

::

    $ emborg due

The :ref:`due command <due>` tells you when the last successful backup was 
performed.

::

    $ emborg info

The :ref:`info command <info>` shows you information about your repository such 
as where it is located and how large it is.

::

    $ emborg check

The :ref:`check command <check>` performs internal consistency checking on your 
repository.

::

    $ emborg prune

The :ref:`prune command <prune>` removes redundant archives.

::

    $ emborg borg check --repair @repo

The :ref:`borg command <borg>` runs a raw *Borg* command for you.  The benefit 
of having *Emborg* run *Borg* for you is that it automatically sets the 
passphrase and the path to the repository so you do not need to remember them.

::

    $ emborg help

The :ref:`help command <help>` shows you information on how to use *Emborg*.


Borg
----

*Borg* has considerably more power than what is exposed with *Emborg*.  You may
use it directly or through the *Emborg* *borg* command when you need that power.
More information about *Borg* can be found at `borgbackup on readthedocs
<https://borgbackup.readthedocs.io/en/stable/index.html>`_.


Precautions
-----------

You should assure you have a backup copy of the encryption key and its
passphrase in a safe place (run 'borg key export' to extract the encryption
keys).  This is very important.  If the only copy of the encryption credentials
are on the disk being backed up and if that disk were to fail you would not be
able to access your backups. I recommend the use of `SpareKeys
<https://github.com/kalekundert/sparekeys>`_ as a way of assuring that you
always have access to the essential information, such as your Borg passphrase
and keys, that you would need to get started after a catastrophic loss of your
disk.

If you keep the passphrase in an *Emborg* configuration file then you should set
the permissions for that file so that it is not readable by others::

   chmod 600 ~/.config/emborg/*

Better is to simply not store the passphrase in *Emborg* configuration files.
You can use the *passcommand* setting for this, or you use
`Avendesora <https://avendesora.readthedocs.io>`_, which is a flexible password
management system. The interface to *Avendesora* is already built in to 
*Emborg,* but its use is optional (it need not be installed).

It is also best, if it can be arranged, to keep your backups at a remote site so
that your backups do not get destroyed in the same disaster, such as a fire or
flood, that claims your original files. One option is `rsync.net
<https://www.rsync.net/products/attic.html>`_. Another is `BorgBase
<https://www.borgbase.com>`_. I have experience with both, and both seem quite 
good.

Finally, it is a good idea to practice a recovery. Pretend that you have lost
all your files and then see if you can do a restore from backup. Doing this and
working out the kinks before you lose your files can save you if you ever do
lose your files.


Issues
------

Please ask questions or report problems on
`Github <https://github.com/KenKundert/emborg/issues>`_.


Contents
--------

.. toctree::
   :maxdepth: 1

   installing
   commands
   configuring
   examples
   api
   utilities
   releases

* :ref:`genindex`
