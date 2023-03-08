.. Emborg documentation master file

Emborg — Front-End to Borg Backup
=================================

| Version: 1.34.1
| Released: 2023-03-08
| Please report all bugs and suggestions on GitHub_.


What is Emborg?
---------------

*Emborg* is a simple command line utility to orchestrate backups. It is built as 
a front-end to Borg_, a powerful and fast de-duplicating backup program.  With 
*Emborg*, you specify all the details about your backups once in advance, and 
then use a very simple command line interface for your day-to-day activities.

Use of *Emborg* does not preclude the use of *Borg* directly on the same 
repository.  The philosophy of *Emborg* is to provide commands that you would 
use often and in an interactive manner with the expectation that you would use 
*Borg* directly for more unusual or esoteric situations.


Why Emborg?
-----------

There are alternatives to *Emborg* such as BorgMatic_ and Vorta_, both of which 
are also front-ends to *BorgBackup*.  *BorgMatic* has a command line interface 
like *Emborg* while *Vorta* is GUI-based.  *Emborg* distinguishes itself by 
providing a command line interface that is very efficient for common tasks, such 
as creating archives (backups), restoring files or directories, or comparing 
existing files to those in an archive.  Also, *Emborg* naturally supports 
multiple destination repositories.  This feature can be used to simultaneously 
backup to a local repository, which provides rapid restores, and an off-site 
repository, which provides increased safety in case of a local disaster.


Why Borg?
---------

Well, everyone needs to backup their files. So perhaps the questions should be: 
why not *Duplicity*?  Duplicity_ has been the standard way to do backups on Unix 
systems for many years.

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

After living with *Duplicity* for many years, I now find the *Borg* recovery 
process stunningly fast and extremely reliable.  I am completely sold on *Borg* 
and will never use *Duplicity* again.


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
so by adding configuration files to ~/.config/emborg. At least two are required.  
First is the file that contains settings that are shared between all 
configurations. This is a Python file located at ``~/.config/emborg/settings``.  
Here is an example:

.. code-block:: bash

    # configurations
    configurations = ['root']
    default_configurations = 'root'

    # things to exclude
    exclude_caches = True
    exclude_if_present = '.nobackup'
    exclude_nodump = True

There also must be individual settings files for each backup configuration.  
They are also a Python files.  The above file defines the *root* configuration.  
The configuration is described in ``~/.config/emborg/root``, an example of which 
is given below.  It is designed to back up the whole machine:

.. code-block:: bash

    # destination repository
    repository = 'borgbase:backups'
    prefix = '{host_name}-{config_name}-'

    # directories to back up
    src_dirs = ['/']

    # directories to exclude
    excludes = [
        "/dev",
        "/proc",
        "/run",
        "/sys",
        "/tmp",
        "/var/cache",
        "/var/tmp",
    ]

Since this configuration needs to back up files that may not be accessible by 
normal users, it should be run by the root user.

Once you have created these files, you can use *Emborg* to perform common tasks 
that involve your backups.

The first step would be to initialize the remote repository.  A repository must 
be initialized before it can first used.  To do so, one uses the :ref:`init 
command <init>`:

.. code-block:: bash

    $ emborg init

Once the repository is initialized, it is ready for use.  The :ref:`create 
command <create>` creates an archive, meaning that it backs up your current 
files.

.. code-block:: bash

    $ emborg create

Once one or more archives have been created, you can list the available archives 
using the :ref:`list command <list>`.

.. code-block:: bash

    $ emborg list

The :ref:`manifest or files command <manifest>` displays all the files in the 
most recent archive.

.. code-block:: bash

    $ emborg manifest
    $ emborg files

You can restrict the listing to those files contained in the current working 
directory using:

.. code-block:: bash

    $ emborg manifest .

If you give the name of an archive, it displays all the files in the specified 
archive.

.. code-block:: bash

    $ emborg manifest -a continuum-2019-04-23T18:35:33

Or, you can give a date, in which case the oldest archive created before that 
date is used.

.. code-block:: bash

    $ emborg manifest -d 2019-04-23

You can also specify the date and time relative to the current moment:

.. code-block:: bash

    $ emborg manifest -d 1w

The :ref:`compare command <compare>` allows you to see and manage the 
differences between your local files and those in an archive.  You can compare 
individual files or entire directories.  You can use the date and archive 
options to select the particular archive to compare against.  You can use the 
interactive version of the command to graphically view changes and merge them 
back into you local files.

.. code-block:: bash

    $ emborg compare -i doc/thesis

The :ref:`restore command <restore>` restores files or directories in place, 
meaning it replaces the current version with the one from the archive.
You can also use the date and archive options to select the particular archive 
to draw from.

.. code-block:: bash

    $ cd ~/bin
    $ emborg restore accounts.json

The :ref:`mount command <mount>` creates a directory 'BACKUPS' and then mounts 
an archive or the whole repository on this directory.  This allows you to move 
into the archive or repository, navigating, examining, and retrieving files as 
if it were a file system.  Again, you can use the date and archive options to 
select the particular archive to mount.

.. code-block:: bash

    $ emborg mount BACKUPS

The :ref:`umount command <umount>` un-mounts the archive or repository after you 
are done with it.

.. code-block:: bash

    $ emborg umount BACKUPS

The :ref:`due command <due>` tells you when the last successful backup was 
performed.

.. code-block:: bash

    $ emborg due

The :ref:`info command <info>` shows you information about your repository such 
as where it is located and how large it is.

.. code-block:: bash

    $ emborg info

The :ref:`help command <emborg_help>` shows you information on how to use 
*Emborg*.

.. code-block:: bash

    $ emborg help

There are more commands, but the above are the most commonly used.


Status
------

*Emborg* includes a utility, *emborg_overdue*, that can be run in a cron script 
on either the client or the server machine that notifies you if your back-ups 
have not completed successfully in a specified period of time.  In addition, 
*Emborg* can be configured to update monitoring services such as 
HealthChecks.io_ with the status of the backups.


Borg
----

*Borg* has more power than what is exposed with *Emborg*.  You may
use it directly or through the *Emborg* :ref:`borg command <borg>` when you need 
that power.  More information can be found at Borg_.


Precautions
-----------

You should assure you have a backup copy of the encryption key and its
passphrase in a safe place (run 'borg key export' to extract the encryption
keys).  This is very important.  If the only copy of the encryption credentials
are on the disk being backed up and if that disk were to fail you would not be
able to access your backups. I recommend the use of SpareKeys_ as a way of 
assuring that you always have access to the essential information, such as your 
*Borg* passphrase and keys, that you would need to get started after 
a catastrophic loss of your disk.

If you keep the passphrase in an *Emborg* configuration file then you should set
the permissions for that file so that it is not readable by others:

.. code-block:: bash

   chmod 600 ~/.config/emborg/*

Better is to simply not store the passphrase in *Emborg* configuration files.
You can use the *passcommand* setting for this, or you can use Avendesora_, 
which is a flexible password management system. The interface to *Avendesora* is 
already built in to *Emborg,* but its use is optional (it need not be 
installed).

It is also best, if it can be arranged, to keep your backups at a remote site so
that your backups do not get destroyed in the same disaster, such as a fire or
flood, that claims your original files. One option is RSync_.  Another is 
BorgBase_.  I have experience with both, and both seem quite good.  One I have 
not tried is Hetzner_.

Finally, it is a good idea to practice a recovery. Pretend that you have lost
all your files and then see if you can do a restore from backup. Doing this and
working out the kinks before you lose your files can save you if you ever do
lose your files.


Issues
------

Please ask questions or report problems on GitHub_.


Contents
--------

.. toctree::
   :maxdepth: 1

   installing
   commands
   configuring
   monitoring
   accessories
   examples
   api
   releases

* :ref:`genindex`

.. _Borg: https://borgbackup.readthedocs.io
.. _BorgMatic: https://torsion.org/borgmatic
.. _Vorta: https://github.com/borgbase/vorta
.. _Duplicity: http://duplicity.nongnu.org
.. _HealthChecks.io: https://healthchecks.io
.. _SpareKeys: https://github.com/kalekundert/sparekeys
.. _Avendesora: https://avendesora.readthedocs.io
.. _RSync: https://www.rsync.net/products/attic.html
.. _BorgBase: https://www.borgbase.com
.. _Hetzner: https://www.hetzner.com/storage/storage-box
.. _GitHub: https://github.com/KenKundert/emborg/issues
