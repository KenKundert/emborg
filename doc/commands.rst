.. _commands:

Commands
========

You invoke *Emborg* from your shell by entering a line of the form::

    $ emborg [global-options] <command> [command-options]

Details about the options and commands can be accessed with::

    $ emborg help

or::

    $ emborg help <command>

The available commands are:

    :borg:       :ref:`run a raw borg command. <borg>`
    :breaklock:  :ref:`breaks the repository and cache locks. <breaklock>`
    :check:      :ref:`checks the repository and its archives <check>`
    :configs:    :ref:`list available backup configurations <configs>`
    :create:     :ref:`create an archive of the current files <create>`
    :delete:     :ref:`delete an archive currently contained in the repository <delete>`
    :diff:       :ref:`show the differences between two archives <diff>`
    :due:        :ref:`days since last backup <due>`
    :extract:    :ref:`recover file or files from archive <extract>`
    :help:       :ref:`give information about commands or other topics <help>`
    :info:       :ref:`print information about a backup <info>`
    :init:       :ref:`initialize the repository <init>`
    :list:       :ref:`list the archives currently contained in the repository <list>`
    :log:        :ref:`print logfile for the last emborg run <log>`
    :manifest:   :ref:`list the files contained in an archive <manifest>`
    :mount:      :ref:`mount a repository or archive <mount>`
    :prune:      :ref:`prune the repository of excess archives <prune>`
    :restore:    :ref:`recover file or files from archive in place <restore>`
    :settings:   :ref:`list settings of chosen configuration <settings>`
    :umount:     :ref:`un-mount a previously mounted repository or archive <umount>`
    :version:    :ref:`display emborg version <version>`

These commands are described in more detail below.  Not everything is described 
here. Run ``emborg help <cmd>`` for the details.


.. _borg:

Borg
----

Runs raw *Borg* commands. Before running the passphrase or passcommand is set.  
Also, if ``@repo`` is found on the command line, it is replaced by the path to 
the repository.

::

    $ emborg borg key export @repo key.borg
    $ emborg borg list @repo::root-2020-04-11T23:38:37


.. _breaklock:

BreakLock
---------

This command breaks the repository and cache locks. Please use carefully and 
only while no *Borg* process (on any machine) is trying to access the Cache or 
the Repository.

::

    $ emborg break-lock
    $ emborg breaklock


.. _check:

Check
-----

Check the integrity of the repository and its archives.  The most recently 
created archive is checked if one is not specified unless ``--all`` is given, in 
which case all archives are checked.


.. _configs:

Configs
-------

List the available backup configurations.  Each configuration corresponds to 
a settings file in your configuration directory (~/.config/emborg). Settings 
common to all your configurations should be placed in ~/.config/emborg/settings.  
You can see available configurations using::

    $ emborg configs

To run a command on a specific configuration, add --config=<cfg> or -c cfg 
before the command. For example::

    $ emborg -c home create


.. _create:

Create
------

This creates an archive in an existing repository. An archive is a snapshot of 
your files as they currently exist.  Borg is a de-duplicating backup program, so 
only the changes from the already existing archives are saved.

::

    $ emborg create

Before creating your first archive, you must use the :ref:`init <init>` command 
to initialize your repository.

This is the default command, so you can create an archive with simply::

    $ emborg

If the backup seems to be taking a long time for no obvious reason, run the 
backup in verbose mode::

    $ emborg -v create

This can help you understand what is happening.


.. _delete:

Delete
------

Delete an archive currently contained in the repository::

    $ emborg delete continuum-2018-12-05T19:23:09

Only one archive can be deleted per command invocation. Add ``--latest`` to 
delete the most recent archive.


.. _diff:

Diff
----

Shows the differences between two archives::

    $ emborg diff continuum-2018-12-05T19:23:09 continuum-2018-12-04T17:41:28


.. _due:

Due
---

When run with no options it indicates when the last backup was created.  For 
example::

    $ emborg due
    backup was performed 19 hours ago.

Adding the --days option results in the message only being printed if the backup 
has not been performed within the specified number of days. Adding the --email 
option results in the message being sent to the specified address rather than 
printed.  This allows you to run the :ref:`due <due>` command from a cron script 
in order to send your self reminders to do a backup if one has not occurred for 
a while.  In these case it is often run with the --no-log option to avoid 
replacing the log file with one that is inherently uninteresting::

    $ emborg --no-log due --days 1 --email me@mydomain.com

You can specify a specific message to be printed with --message. In this case, 
{days} is replaced by the number of days since the last backup. You can add 
floating-point format codes to specify the resolution used. For example: 
{days:.1f}. Also, {elapsed} is replaced with a humanized description of how long 
it has been since the last backup, and {config} is replaced with the name of the 
configuration being reported on. So ``--message '{elapsed} since last backup of 
{config}.'`` might produce something like this::

    12 hours since last backup of home.

With composite configurations the message is printed for each component config 
unless --oldest is specified, in which case only the oldest is displayed.


.. _extract:

Extract
-------

You extract a file or directory from an archive using::

    $ emborg extract home/shaunte/bin

Use manifest to determine what path you should specify to identify the desired 
file or directory.  You can specify more than one path. Usually, they will be 
paths that are relative to ``/``, thus the paths should look like absolute paths 
with the leading slash removed.  The paths may point to directories, in which 
case the entire directory is extracted.  It may also be a glob pattern.

If you do not specify an archive or date, the most recent archive is used.  You 
can extract the version of a file or directory that existed on a particular date 
using::

    $ emborg extract --date 2015-04-01 home/shaunte/bin

Or, you can extract the version from a particular archive using::

    $ emborg extract --archive continuum-2018-12-05T12:54:26 home/shaunte/bin

The extracted files are placed in the current working directory with
the original hierarchy. Thus, the above commands create the directory::

    ./home/shaunte/bin

See the :ref:`restore <restore>` command as an alternative to *extract* that 
replaces the existing files rather than simply copying them into the current 
directory.


.. _help:

Help
----

Show information about Emborg::

    $ emborg help

You can ask for help on a specific command or topic with::

    $ emborg help <topic>

For example::

    $ emborg help extract


.. _info:

Info
----

This command prints out the locations of important files and directories.

::

    $ emborg info


.. _init:

Init
----

Initializes a Borg repository. This must be done before you create your first 
archive.

::

    $ emborg init


.. _list:

List
----

List available archives.

::

    $ emborg list


.. _log:

Log
---

Show the logfile from the previous run.

::

    $ emborg log


.. _manifest:

Manifest
--------

Once a backup has been performed, you can list the files available in your 
archive using::

    $ emborg manifest

If you do not specify an archive, as above, the latest archive is used.

You can explicitly specify an archive::

    $ emborg manifest --archive continuum-2015-04-01T12:19:58

Or you can list the files that existed on a particular date using::

    $ emborg manifest --date 2015-04-01

The *manifest* command provides a variety of sorting and formatting options. The 
formatting options are under the control of the :ref:`manifest_formats` setting.  
For example::

    $ emborg manifest

This outputs the files in the order and with the format produced by Borg.

::

    $ emborg manifest -l
    $ emborg manifest -n

These use the Borg order but shorten the lines by reducing the amount of fields 
they contain. With ``-l`` the *long* format is used, which by default contains 
the size, the date, and the path. With ``-n`` the *name* is used, which by 
default contains only the path.

Finally::

    $ emborg manifest -S
    $ emborg manifest -D

The first sorts the files by size. It uses the *size* format, which by default 
contains only the size and the path.
The second sorts the files by modification date. It uses the *date* format, 
which by default contains the day, date, time and the path.
More choices are available; run ``emborg help manifest`` for the details.

You can use ``files`` as an alias for ``manifest``.

    $ emborg files


.. _mount:

Mount
-----

Once a backup has been performed, you can mount it and then look around as you 
would a normal read-only filesystem.

::

    $ emborg mount backups

In this example, *backups* acts as a mount point. If it exists, it must be 
a directory. If it does not exist, it is created.

If you do not specify a mount point, the value of *default_mount_point* setting 
is used if set.

If you do not specify an archive, as above, the most recently created archive
is mounted.

You can explicitly specify an archive::

    $ emborg mount --archive continuum-2015-04-01T12:19:58 backups

You can mount the files that existed on a particular date using::

    $ emborg mount --date 2015-04-01 backups

Or, you can mount all the available archives::

    $ emborg mount --all backups

You will need to un-mount the repository or archive when you are done with it.  
To do so, use the :ref:`umount <umount>` command.


.. _prune:

Prune
-----

Prune the repository of excess archives.  You can use the :ref:`keep_within`, 
:ref:`keep_last`, :ref:`keep_minutely`, :ref:`keep_hourly`, :ref:`keep_daily`, 
:ref:`keep_weekly`, :ref:`keep_monthly`, and :ref:`keep_yearly` settings to 
control which archives should be kept. At least one of these settings must be 
specified to use :ref:`prune <prune>`::

    $ emborg prune


.. _restore:

Restore
-------

This command is very similar to the :ref:`extract <extract>` command except that 
it is meant to be run in place. Thus, the paths given are converted to absolute 
paths and then the borg :ref:`extract <extract>` command is run from the root 
directory (/) so that the existing files are replaced by the extracted files.

For example, the following commands restore your .bashrc file::

    $ cd ~
    $ emborg restore .bashrc


.. _settings:

Settings
--------

This command displays all the settings that affect a backup configuration.

::

    $ emborg settings

Add ``--all`` option to list out all available settings and their descriptions 
rather than the settings actually specified and their values.


.. _umount:

Umount
------

Un-mount a previously mounted repository or archive::

    $ emborg umount backups
    $ rmdir backups

where *backups* is the existing mount point.

If you do not specify a mount point, the value of *default_mount_point* setting 
is used if set.


.. _version:

Version
-------

Prints the *Emborg* version.

::

    $ emborg version
