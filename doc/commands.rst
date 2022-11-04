.. _commands:

Commands
========

You invoke *Emborg* from your shell by entering a line of the form:

.. code-block:: bash

    $ emborg [global-options] <command> [command-options]

Details about the options and commands can be accessed with:

.. code-block:: bash

    $ emborg help

or:

.. code-block:: bash

    $ emborg help <command>

The available commands are:

    :borg:       :ref:`run a raw borg command <borg>`
    :breaklock:  :ref:`breaks the repository and cache locks <breaklock>`
    :check:      :ref:`checks the repository and its archives <check>`
    :compact:    :ref:`compact segment files in the repository <compact>`
    :compare:    :ref:`compare local files with those in an archive <compare>`
    :configs:    :ref:`list available backup configurations <configs>`
    :create:     :ref:`create an archive of the current files <create>`
    :delete:     :ref:`delete an archive currently contained in the repository <delete>`
    :diff:       :ref:`show the differences between two archives <diff>`
    :due:        :ref:`days since last backup <due>`
    :extract:    :ref:`recover file or files from archive <extract>`
    :help:       :ref:`give information about commands or other topics <emborg_help>`
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


.. _exit status:

Exit Status
-----------

*Emborg* returns with an exit status of 0 if it completes without issue.  It 
returns with an exit status of 1 if was able to terminate normally but some 
exceptional condition was encountered along the way.  For example, if the 
:ref:`compare <compare>` or :ref:`diff <diff>` detects a difference or if 
:ref:`due <due>` command detects the backups are overdue, a 1 is returned.  In 
addition, 1 is returned if *Borg* detects an error but is able to complete 
anyway. However, if *Emborg* or *Borg* suffers errors and cannot complete, 2 is 
returned.


.. _borg:

Borg
----

Runs raw *Borg* commands. Before running the passphrase or passcommand is set.  
Also, if ``@repo`` is found on the command line, it is replaced by the path to 
the repository.

.. code-block:: bash

    $ emborg borg key export @repo key.borg
    $ emborg borg list @repo::root-2020-04-11T23:38:37

*Emborg* runs the *Borg* command from :ref:`working_dir` if it is specified and 
``/`` if not.


.. _breaklock:

BreakLock
---------

This command breaks the repository and cache locks. Please use carefully and 
only while no *Borg* process (on any machine) is trying to access the Cache or 
the Repository.

.. code-block:: bash

    $ emborg break-lock
    $ emborg breaklock


.. _check:

Check
-----

Check the integrity of the repository and its archives.  The most recently 
created archive is checked if one is not specified unless ``--all`` is given, in 
which case all archives are checked.

The ``--repair`` option attempts to repair any damage found. Be aware that this 
is considered an *experimental* feature in *Borg* and so carries extra risk due 
to its immaturity.


.. _compact:

Compact
-------

This command frees repository space by compacting segments.

Use this regularly to avoid running out of space, however you do not need to it 
after each *Borg* command. It is especially useful after deleting archives, 
because only compaction really frees repository space.

Requires Borg version 1.2 or newer.  Prior to version 1.2 the compact 
functionality was part of the *Borg* *prune* command.  As of version 1.2 this 
functionality was split into its own command.

If you set :ref:`compact_after_delete` *Emborg* automatically runs this command 
after every use of the :ref:`delete <delete>` and :ref:`prune <prune>` commands.


.. _compare:

Compare
-------

Reports and allows you to manage the differences between your local files and 
those in an archive.  The base command simply reports the differences:

.. code-block:: bash

    $ emborg compare

The ``--interactive`` option allows you to manage those differences.  
Specifically, it will open an interactive file comparison tool that allows you 
to compare the contents of your files and copy differences from the files in the 
archive to your local files:

.. code-block:: bash

    $ emborg compare -i

You can specify the archive by name or by date or age.  If you do not you will 
use the most recent archive:

.. code-block:: bash

    $ emborg compare -a continuum-2020-12-04T17:41:28
    $ emborg compare -d 2020-12-04
    $ emborg compare -d 1w

You can specify a path to a file or directory to compare, if you do not you will 
compare the files and directories of the current working directory.

.. code-block:: bash

    $ emborg compare tests
    $ emborg compare ~/bin

This command uses external tools to view and manage the differences.  Before it 
can be used it must be configured to use these tools, which is done with the
:ref:`manage_diffs_cmd` and :ref:`report_diffs_cmd` settings.  In addition, the 
:ref:`default_mount_point` must be configured.  The :ref:`manage_diffs_cmd` is 
used if the ``--interactive`` (or ``-i``) option is given, and 
:ref:`report_diffs_cmd` otherwise.  However, if only one is given it is used in 
both cases.  So, if you find that you only want to use the interactive tool to 
view and manage your differences, you can simply not specify 
:ref:`report_diffs_cmd`, which would eliminate the need to specify the ``-i`` 
option.

The command operates by mounting the desired archive, performing the comparison, 
and then unmounting the directory. Problems sometimes occur that can result in 
the archive remaining mounted.  In this case you will need to resolve any issues 
that are preventing the unmounting, and then explicitly run the :ref:`umount 
command <umount>` before you can use this *Borg* repository again.

This command differs from the :ref:`diff command <diff>` in that it compares 
local files to those in an archive where as :ref:`diff <diff>` compares the 
files contained in two archives.


.. _configs:

Configs
-------

List the available backup configurations.  Each configuration corresponds to 
a settings file in your configuration directory (~/.config/emborg). Settings 
common to all your configurations should be placed in ~/.config/emborg/settings.  
You can see available configurations using:

.. code-block:: bash

    $ emborg configs

To run a command on a specific configuration, add --config=<cfg> or -c cfg 
before the command. For example:

.. code-block:: bash

    $ emborg -c home create


.. _create:

Create
------

This creates an archive in an existing repository. An archive is a snapshot of 
your files as they currently exist.  Borg is a de-duplicating backup program, so 
only the changes from the already existing archives are saved.

.. code-block:: bash

    $ emborg create

Before creating your first archive, you must use the :ref:`init <init>` command 
to initialize your repository.

This is the default command, so you can create an archive with simply:

.. code-block:: bash

    $ emborg

If the backup seems to be taking a long time for no obvious reason, run the 
backup in verbose mode:

.. code-block:: bash

    $ emborg -v create

This can help you understand what is happening.

*Emborg* runs the *create* command from :ref:`working_dir` if it is specified 
and current directory if not.


.. _delete:

Delete
------

Delete an archive currently contained in the repository:

.. code-block:: bash

    $ emborg delete continuum-2020-12-05T19:23:09

Only one archive can be deleted per command invocation. If an archive is not 
given, the latest is deleted.

Specifying ``--repo`` results in the entire repository being deleted.


.. _diff:

Diff
----

Shows the differences between two archives:

.. code-block:: bash

    $ emborg diff continuum-2020-12-05T19:23:09 continuum-2020-12-04T17:41:28

You can constrain the output listing to only those files in a particular 
directory by adding that path to the end of the command:

.. code-block:: bash

    $ emborg diff continuum-2020-12-05T19:23:09 continuum-2020-12-04T17:41:28 .

This command differs from the :ref:`compare command <compare>` in that it only 
reports a list of files that differ between two archives, whereas :ref:`compare 
<compare>` shows how local files differ from those in an archive and can show 
you the contents of those files and allow you interactively copy changes from 
the archive to your local files.


.. _due:

Due
---

When run with no options it indicates when the last backup was created.  For 
example:

.. code-block:: bash

    $ emborg due
    backup was performed 19 hours ago.

Adding the --days option results in the message only being printed if the backup 
has not been performed within the specified number of days. Adding the --email 
option results in the message being sent to the specified address rather than 
printed.  This allows you to run the :ref:`due <due>` command from a cron script 
in order to send your self reminders to do a backup if one has not occurred for 
a while.  In these case it is often run with the --no-log option to avoid 
replacing the log file with one that is inherently uninteresting:

.. code-block:: bash

    $ emborg --no-log due --days 1 --email me@mydomain.com

You can specify a specific message to be printed with --message. In this case, 
{days} is replaced by the number of days since the last backup. You can add 
floating-point format codes to specify the resolution used. For example: 
{days:.1f}. Also, {elapsed} is replaced with a humanized description of how long 
it has been since the last backup, and {config} is replaced with the name of the 
configuration being reported on. So ``--message '{elapsed} since last backup of 
{config}.'`` might produce something like this:

.. code-block:: text

    12 hours since last backup of home.

With composite configurations the message is printed for each component config 
unless --oldest is specified, in which case only the oldest is displayed.


.. _extract:

Extract
-------

You extract a file or directory from an archive using:

.. code-block:: bash

    $ emborg extract home/shaunte/bin

Use manifest to determine what path you should specify to identify the desired 
file or directory.  You can specify more than one path. Usually, they will be 
paths that are relative to ``/``, thus the paths should look like absolute paths 
with the leading slash removed.  The paths may point to directories, in which 
case the entire directory is extracted.  It may also be a glob pattern.

By default, the most recent archive is used, however, if desired you can 
explicitly specify a particular archive. For example:

.. code-block:: bash

    $ emborg extract --archive continuum-2020-12-05T12:54:26 home/shaunte/bin

Alternatively you can specify a date or date and time.  If only the date is 
given the time is taken to be midnight.  The oldest archive that is younger than 
specified date and time is used. For example:

.. code-block:: bash

    $ emborg extract --date 2021-04-01 home/shaunte/bin
    $ emborg extract --date 2021-04-01T15:30 home/shaunte/bin

Alternatively, you can specify the date in relative terms:

.. code-block:: bash

    $ emborg extract --date 3d  home/shaunte/bin

In this case 3d means 3 days. You can use s, m, h, d, w, M, and y to represent 
seconds, minutes, hours, days, weeks, months, and years.

The extracted files are placed in the current working directory with
the original hierarchy. Thus, the above commands create the directory:

.. code-block:: text

    ./home/shaunte/bin

See the :ref:`restore <restore>` command as an alternative to *extract* that 
replaces the existing files rather than simply copying them into the current 
directory.


.. _emborg_help:

Help
----

Show information about Emborg:

.. code-block:: bash

    $ emborg help

You can ask for help on a specific command or topic with:

.. code-block:: bash

    $ emborg help <topic>

For example:

.. code-block:: bash

    $ emborg help extract


.. _info:

Info
----

This command prints out the locations of important files and directories.

.. code-block:: bash

    $ emborg info

You can also get information about a particular archive.

.. code-block:: bash

    $ emborg info home-2022-11-03T23:07:25


.. _init:

Init
----

Initializes a Borg repository. This must be done before you create your first 
archive.

.. code-block:: bash

    $ emborg init


.. _list:

List
----

List available archives.

.. code-block:: bash

    $ emborg list


.. _log:

Log
---

Show the log from the previous run.

.. code-block:: bash

    $ emborg log

Most commands save a log file, but some do not.
Specifically,
:ref:`configs <configs>`,
:ref:`due <due>`,
:ref:`help <emborg_help>`,
:ref:`log <log>`,
:ref:`settings <settings>` and
:ref:`version <version>` do not.
Additionally, no command will save a log file if the ``--no-log`` command line 
option is specified.  If you need to debug a command that does not normally 
generate a log file and would like the extra detail that is normally included in 
the log, specify the ``--narrate`` command line option.

If you wish to access the log files directly, they reside in 
``~/.local/share/emborg``.


.. _manifest:

Manifest
--------

Once a backup has been performed, you can list the files available in your 
archive using:

.. code-block:: bash

    $ emborg manifest

You specify a path.  If so, the files listed are those contained within that 
path.  For example:

.. code-block:: bash

    $ emborg manifest .
    $ emborg manifest -R .

The first command lists the files in the archive that were originally contained 
in the current working directory.  The second lists the files that were in 
specified directory and any sub directories.

If you do not specify an archive, as above, the latest archive is used.

You can explicitly specify an archive:

.. code-block:: bash

    $ emborg manifest --archive continuum-2021-04-01T12:19:58

Or you choose an archive based on a date and time.  The oldest archive that is 
younger than specified date and time is used.

.. code-block:: bash

    $ emborg manifest --date 2021-04-01
    $ emborg manifest --date 2021-04-01T12:45

You can also specify the date in relative terms:

.. code-block:: bash

    $ emborg manifest --date 1w

where s, m, h, d, w, M, and y represents seconds, minutes, hours, days, weeks, 
months, and years.

The *manifest* command provides a variety of sorting and formatting options. The 
formatting options are under the control of the :ref:`manifest_formats` setting.  
For example:

.. code-block:: bash

    $ emborg manifest

This outputs the files in the order and with the format produced by Borg.
If a line is green if the corresponding file is healthy, and if red it is broken 
(see `Borg list command
<https://borgbackup.readthedocs.io/en/stable/usage/list.html#description>`_ for 
more information on broken files).

.. code-block:: bash

    $ emborg manifest -l
    $ emborg manifest -n

These use the Borg order but change the amount of information shown.  With 
``-l`` the *long* format is used, which by default contains the size, the date, 
and the path. With ``-n`` the *name* is used, which by default contains 
only the path.

Finally:

.. code-block:: bash

    $ emborg manifest -S
    $ emborg manifest -D

The first sorts the files by size. It uses the *size* format, which by default 
contains only the size and the path.  The second sorts the files by modification 
date. It uses the *date* format, which by default contains the day, date, time 
and the path.  More choices are available; run ``emborg help manifest`` for the 
details.

You can use ``files`` as an alias for ``manifest``:

.. code-block:: bash

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

You can explicitly specify an archive:

.. code-block:: bash

    $ emborg mount --archive continuum-2015-04-01T12:19:58 backups

You can mount the files that existed on a particular date using:

.. code-block:: bash

    $ emborg mount --date 2021-04-01 backups
    $ emborg mount --date 2021-04-01T18:30 backups

If the time is not given, it is taken to be midnight.

You can also specify the date in relative terms:

.. code-block:: bash

    $ emborg mount --date 1w backups

where s, m, h, d, w, M, and y represents seconds, minutes, hours, days, weeks, 
months, and years.

When a date is given, the oldest archive that is younger than the specified date 
or time is used.

Finally, you can mount all the available archives:

.. code-block:: bash

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
specified to use :ref:`prune <prune>`:

.. code-block:: bash

    $ emborg prune


.. _restore:

Restore
-------

This command is very similar to the :ref:`extract <extract>` command except that 
it is meant to be run in place. Thus, the paths given are converted to absolute 
paths and then the borg :ref:`extract <extract>` command is run from the root 
directory (/) so that the existing files are replaced by the extracted files.

For example, the following commands restore your .bashrc file:

.. code-block:: bash

    $ cd ~
    $ emborg restore .bashrc

*Emborg* runs the *restore* command from :ref:`working_dir` if it is specified 
and the current directory if not.

By default, the most recent archive is used, however, if desired you can 
explicitly specify a particular archive. For example:

    $ emborg restore --archive continuum-2020-12-05T12:54:26 resume.doc

Or you choose an archive based on a date and time.  The oldest archive that is 
younger than specified date and time is used.

    $ emborg restore --date 2021-04-01 resume.doc
    $ emborg restore --date 2021-04-01T18:30 resume.doc

Or you can specify the date in relative terms:

    $ emborg restore --date 3d  resume.doc

In this case 3d means 3 days. You can use s, m, h, d, w, M, and y to
represent seconds, minutes, hours, days, weeks, months, and years.

This command is very similar to the :ref:`extract <extract>` command except that 
it is meant to replace files in place.  It also takes similar options.


.. _settings:

Settings
--------

This command displays all the settings that affect a backup configuration.

.. code-block:: bash

    $ emborg settings

Add ``--all`` option to list out all available settings and their descriptions 
rather than the settings actually specified and their values.


.. _umount:

Umount
------

Un-mount a previously mounted repository or archive:

.. code-block:: bash

    $ emborg umount backups
    $ rmdir backups

where *backups* is the existing mount point.

If you do not specify a mount point, the value of *default_mount_point* setting 
is used if set.


.. _version:

Version
-------

Prints the *Emborg* version.

.. code-block:: bash

    $ emborg version
