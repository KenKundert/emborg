emborg -- Encrypted Backups to a Remote Server
==============================================

| Version: 0.1.5
| Released: 2018-12-07
|

Emborg is a simple command line utility to orchestrate backups. It is built as 
a front-end to Borg, a powerful and fast deduplicating backup program.  With 
Emborg, you specify all the details about your backups once in advance, and 
then use a very simple command line interface for your day-to-day activities.  
The details are contained in ~/.config/emborg.  That directory contains a file 
(settings) that contains shared settings, and then another file for each backup 
configuration you have.


Commands
========

Create
------

This creates an archive in an existing repository. An archive is a snapshot of 
your files as they currently exist.  Borg is a de-duplicating backup program, so 
only the changes from the already existing archives are saved.

    emborg create

Before creating your first archive, you must use the *init* command to 
initialize your repository.


Check
-----

Check the integrity of the repository and its archives.


Configs
-------

List the available backup configurations.  Each configuration will correspond to 
a settings file in your configuration directory (~/.config/emborg). Settings 
common to all your configurations should be placed in ~/.config/emborg/settings.  
You can see available configs using::

    emborg configs

To run a command on a specific configuration, add --config=<cfg> or -c cfg 
before the command. For example::

    emborg -c home create


Diff
----

Shows the differences between two archives::

    > emborg diff kundert-2018-12-05T19:23:09 kundert-2018-12-04T17:41:28


Due
---

When run with no options it indicates when the last backup was created.  For 
example::

    > emborg due
    backup was performed 19 hours ago.

You can also specify options that result in an output message if a time limit 
has been exceeded. This allow you to use this with status bar programs such as 
i3status to generate reminders.


Extract
-------

You extract a file or directory from an archive using::

   emborg extract home/ken/bin

Use manifest to determine what path you should specify to identify the desired 
file or directory (they will paths relative to /).  Thus, the paths should look 
like absolute paths with the leading slash removed.  The paths may point to 
directories, in which case the entire directory is extracted. It may also be 
a glob pattern.

If you do not specify an archive or date, the most recent archive is used.  You 
can extract the version of a file or directory that existed on a particular date 
using:

    emborg extract --date 2015-04-01 home/ken/bin

Or, you can extract the version from a particular archive using:

    emborg extract --archive kundert-2018-12-05T12:54:26 home/ken/bin

The extracted files are placed in the current working directory within their 
original hierarchy. Thus, the above commands create the file:

    ./home/ken/bin


Help
----

Show information about Emborg

   emborg help

You can ask for help on a specific command or topic with:

   emborg help <topic>

For example:

   emborg help extract


Info
----

This command prints out the locations of important files and directories.

   emborg info


Init
----

Initializes a Borg repository. This must be done before you create your first 
archive.

   emborg init


List
----

List available archives.

   emborg list


Manifest
--------

Once a backup has been performed, you can list the files available in your 
archive using::

   emborg manifest

If you do not specify an archive, as above, the latest archive is used.

You can explicitly specify an archive::

   emborg manifest --archive kundert-2015-04-01T12:19:58

Or you can list the files that existed on a particular date using::

   emborg manifest --date 2015-04-01


Mount
-----

Once a backup has been performed, you can mount it and then look around as you 
would a normal read-only filesystem.

   emborg mount backups

In this example, backups acts as a mount point. If it exists, it must be 
a directory. If it does not exist, it is created.

If you do not specify an archive, as above, all archives are mounted.

You can explicitly specify an archive::

   emborg mount --archive kundert-2015-04-01T12:19:58 backups

Or you can mount the files that existed on a particular date using::

   emborg mount --date 2015-04-01 backups

You will need to un-mount the repository or archive when you are done with it.  
To do so, use the *umount* command.


Prune
-----

Prune the repository of excess archives.  You can use the *keep_within*, 
*keep_last*, *keep_minutely*, *keep_hourly*, *keep_daily*, *keep_weekly*, 
*keep_monthly*, and *keep_yearly* settings to control which archives should be 
kept. At least one of these settings must be specified to use *prune*::

   emborg prune


Settings
--------

This command displays all the settings that affect a backup configuration.
Add '-a' option to list out all available settings and their descriptions rather 
than the specified settings and their values.


Umount
------

Un-mount a previously mounted repository or archive::

   emborg umount backups
   rmdir backups

where *backups* is the existing mount point.


Version
-------

Prints the *emborg* version.

   emborg version


Configuration
=============

Shared Settings
---------------

Shared settings go in ~/.config/emborg/settings. This is a Python file that 
contains values needed by Emborg. It might look like the following::

    default_configuration = 'home'        # default backup configuration
    configurations = 'home websites'      # available backup configurations
    avendesora_account = 'borg-backup'    # Avendesora account name (holds 
    passphrase for encryption key)
    passphrase = None                     # passphrase to use (if specified, Avendesora is not used)
                                          # if both avendesora_account and passphrase are empty, encryption is not used
    notify = "me@mydomain.com"            # email address to notify when things go wrong
    notifier = 'notify-send -u normal {prog_name} "{msg}"'
                                          # notification program
    bw_limit = 2000                       # bandwidth limit in kbps
    compression = 'lz4'                   # compression algorithm to use
    umask = '77'                          # umask to use when creating the archives
    lock_wait = 5                         # how long to wait for the lock
    keep_hourly = 48                      # number of hourly archives to keep
    keep_daily = 64                       # number of daily archives to keep
    keep_weekly = 52                      # number of weekly archives to keep
    keep_monthly = 48                     # number of weekly archives to keep
    keep_yearly = 24                      # number of weekly archives to keep

If you encrypt your backups, you can specify the encryption key in this file as 
*passphrase*. In this case, you should be careful to assure the file is not 
readable by others (chmod 600 settings).  Alternatively, you can use `Avendesora 
<https://avendesora.readthedocs.io>`_ to securely hold your key by specifying 
the Avendesora account name of the key to *avendesora_account*.


Configuration Settings
----------------------

Each backup configuration must have a settings file in ~/.config/emborg. The 
name of the file is the name of the backup configuration.  It might look like 
the following::

    repository = 'media:/mnt/backups/{host_name}/{config_name}'
                                          # remote directory for backup sets
    archive = '{host_name}-{{now}}'       # naming pattern used for the archives
        # May contain {<name>} where name is any of host_name, user_name, 
        # prog_name config_name, or any of the user specified settings.
        # Double up the braces to specify parameters that should be interpreted 
        # by borg rather than by emborg.
    src_dirs = ['~', '/etc']              # absolute path to directory to be backed up
    excludes = '''
        ~/tmp
        ~/**/.hg
        ~/**/.git
        ~/**/*.pyc
        ~/**/.*.swp
        ~/**/.*.swo
    '''.split()                            # list of glob strings of files or directories to skip
    one_file_system = False
    exclude_caches = True

    # commands to be run before and after backups (run from working directory)
    run_before_backup = [
        './clean-home >& clean-home.log',
            # remove the detritus before backing up
    ]
    run_after_backup = [
        './rebuild-manpages > /dev/null',
            # rebuild my man pages, they were deleted in clean
    ]

    # if set, this file or these files must exist or backups will quit with an error
    must_exist = '~/doc/thesis'

String values may incorporate other string valued settings. Use braces to 
interpolate another setting. In addition, you may interpolate the configuration 
name ('config_name'), the host name ('host_name'), the user name ('user_name') 
or Emborg's program name ('prog_name'). An example of this is shown in 
*dest_dir* above.


Precautions
===========

You should assure you have a backup copy of the passphrase in a safe place.  
This is very important. If the only copy of the passphrase is on the disk being 
backed up, then if that disk were to fail you would not be able to access your 
backups.

If you keep the passphrase in the emborg file, you should set its permissions so 
that it is not readable by others::

   chmod 700 emborg

Better yet is to simply not store the passphrase in the emborg script. This can 
be arranged if you are using `Abraxas <https://github.com/KenKundert/abraxas>`_, 
which is a flexible password management system. The interface to Abraxas is 
already built in to emborg, but its use is optional (it need not be installed).

It is also best, if it can be arranged, to keep your backups at a remote site so 
that your backups do not get destroyed in the same disaster, such as a fire or 
flood, that claims your original files.


Borg
----
*Borg* has considerably more power than what is exposed with *emborg*.  You may 
use it directly when you need that power. More information about *Borg* can be 
found at `borgbackup on readthedocs <https://borgbackup.readthedocs.io/en/stable/index.html>`_.
