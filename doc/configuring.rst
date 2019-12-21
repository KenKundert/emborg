.. _configuring_emborg:

Configuring
===========

Settings file go in ~/.config/emborg. You need a shared settings file and then 
one file for each backup configuration you need.  Except for 
:ref:`configurations` and :ref:`default_configuration` any setting may be place 
in the shared file or the repository specific file.  If a setting is found in 
both files, the version in the configuration specific file dominates.

You can get a complete list of available configuration settings by running::

    emborg settings --available


Shared Settings
---------------

Shared settings go in ~/.config/emborg/settings.  This is a Python file that 
contains values needed by all of your configurations.  It might look like the 
following::

    default_configuration = 'home'        # default backup configuration
    configurations = 'home websites'      # available backup configurations
    avendesora_account = 'borg-backup'    # Avendesora account name (holds passphrase for encryption key)
    passphrase = None                     # passphrase to use (if specified, Avendesora is not used)
    encryption = 'keyfile'                # encryption method
    prune_after_create = True             # run prune as the last step of an archive creation
    check_after_create = 'latest'         # run check as the last step of an archive creation
    notify = "me@mydomain.com"            # email address to notify when things go wrong
    notifier = 'notify-send -u normal {prog_name} "{msg}"'
                                          # program used to send realtime notifications
                                          # generally you use notify or notifier, but not both
                                          # use notifier for interactive backups 
                                          # and notify for scheduled backups
                                          # notification program
    remote_ratelimit = 2000               # bandwidth limit in kbps
    umask = '077'                         # umask to use when creating the archives
    repository = 'archives:/mnt/backups/{host_name}/{user_name}/{config_name}'
                                          # remote directory for repository
    archive = '{host_name}-{{now}}'       # naming pattern used for the archives
        # May contain {<name>} where <name> may be any of host_name, user_name, 
        # prog_name config_name, or any of the user specified settings.
        # Double up the braces to specify parameters that should be interpreted 
        # by borg rather than by emborg.
    exclude_caches = True                 # do not backup directories that contain CACHEDIR.TAG
    exclude_if_present = '.nobackup'      # do not backup directories containing this file
    keep_within = '1d'                    # keep all archives within this time interval
    keep_hourly = '48'                    # number of hourly archives to keep
    keep_daily = '7'                      # number of daily archives to keep
    keep_weekly = '4'                     # number of weekly archives to keep
    keep_monthly = '12'                   # number of weekly archives to keep
    keep_yearly = '2'                     # number of weekly archives to keep

If you encrypt your backups, you can specify the encryption key in this file as 
:ref:`passphrase`. In this case, you should be careful to assure the file is not 
readable by others (chmod 600 settings).  Alternatively, you can use `Avendesora 
<https://avendesora.readthedocs.io>`_ to securely hold your key by specifying 
the Avendesora account name of the key to *avendesora_account*.

This example assumes that there is one backup configuration per repository. You 
can instead have all of your configurations share a single repository replacing 
:ref:`repository` and adding :ref:`prefix` like so::

    repository = 'archives:/mnt/backups/{host_name}/{user_name}'
    prefix = '{config_name}-'


Configurations
--------------

Each backup configuration must have a settings file in ~/.config/emborg. The 
name of the file is the name of the backup configuration.  It might look like 
the following::

    src_dirs = ['~', '/etc']              # absolute paths to directories to be backed up
    excludes = '''
        ~/tmp
        ~/**/.hg
        ~/**/.git
        ~/**/*.pyc
        ~/**/.*.swp
        ~/**/.*.swo
    '''.split()                           # list of glob strings of files or directories to skip
    one_file_system = False               # okay to traverse filesystems

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
or Emborg's program name ('prog_name'). An example of this is shown in both
:ref:`repository` and :ref:`archive` above.  Doubling up the braces acts to 
escape them.  In this way you gain access to *Borg* settings. :ref:`archive` 
shows and example of that.


Includes
--------

Any settings file may include the contents of another file by using
:ref:`include`.  You may either specify a single include file as a string or 
a collection as a list of strings::

    include = 'file-to-include'

or::

    include = ['first-file-to-include', 'second-file-to-include']


Composite Configurations
------------------------

It is possible to define composite configurations that allow you to run several 
configurations at once.  This might be useful if you have files that benefit, 
for example, from different prune schedules.

As an example, consider having three configurations that you would like to run 
all at once. You can specify these configurations as follows::

    configurations = 'home lamp data all=home,lamp,data'

In this case *home*, *lamp*, and *data* are simple configurations and *all* is 
a composite configuration.  *home*, *lamp*, and *data* would have configuration 
files whereas *all* would not.  The composite configuration should be specified 
without spaces.

You can run a specific configuration with:

    emborg -c home extract ~/bin

You can run all three configurations with:

    emborg -c all create

Only certain commands support composite configurations. Specifically, 
:ref:`create`, :ref:`check`, :ref:`configs`, :ref:`due`, :ref:`help`, 
:ref:`info`, :ref:`log`, :ref:`prune`, and :ref:`version` support composite 
configures.  Specifying a composite configuration to a command that does not 
support them results in an error.


Emborg Settings
---------------

These settings control the behavior of *Emborg*.

.. _archive:

archive
~~~~~~~

*archive* is a template that specifies the name of each archive.  A typical 
value might be::

    archive = '{config_name}-{{now}}'

*Emborg* examines the string for names within a single brace-pair and replaces 
them with the value specified by the name. Names within double-brace pairs are 
interpreted by *Borg*.

This template consists of a leading part that is fixed ('{config_name}-') and 
a trailing part that varies on each archive ('{{now}}', which is replaced by 
a datestamp). The leading fixed part is referred to as the *prefix* and can be 
given separately::

    archive = '{config_name}-{{now}}'
    prefix = '{config_name}-'

This is helpful when multiple configurations backup to the same repository. In 
this case *prefix* is assumed to be unique between the configurations. It allows 
certain commands to filter out archives that belong to other configurations.  
Specifically the :ref:`check`, :ref:`delete`, :ref:`info`, :ref:`list`, 
:ref:`mount`, and :ref:`prune` commands all use *prefix*.

When sharing a repository between multiple backup configurations, it is 
important that all prefixes be unique. Be careful of one prefix that is a prefix 
of another. For example, prefixes of *root* and *root2* would be bad because 
*root* is a prefix of *root2*.  In the examples given, *prefix* ends with '-' to 
reduce this risk.

If you do not specify either *archive* or *prefix*, then you get the following 
defaults::

    prefix = '{host_name}-{user_name}-{config_name}-'
    archive = '{prefix}{{now}}'

If you specify only *prefix*, then *archive* becomes::

    archive = '<prefix>{{now}}'

If you specify only *archive*, then *prefix* remains unset. This is only 
suitable when there is only one backup configuration using a repository.

If you want *prefix* and want to customize *now*, you should give both *prefix* 
and *archive*. For example, you can reduce the length of the timestamp using::

    prefix = '{host_name}-'
    archive = '{prefix}{{now:%Y%m%d}}'

In this example the host name was used as the prefix rather than the 
configuration name. When specifying both the *prefix* and the *archive*, the 
leading part of *archive* should match *prefix*.  Be aware that by including 
only the date in the archive name rather than the full timestamp, you are 
limiting yourself to creating one archive per day.


.. _avendesora_account:

avendesora_account
~~~~~~~~~~~~~~~~~~

An alternative to :ref:`passphrase`. The name of the
`Avendesora <https://avendesora.readthedocs.io>`_ account used to hold the 
passphrase for the encryption key. Using *Avendesora* keeps your passphrase out 
of your settings file, but requires that GPG agent be available and loaded with 
your private key.  This is normal when running interactively.  When running 
batch, say from *cron*, you can use the Linux *keychain* command to retain your 
GPG credentials for you.


.. _avendesora_field:

avendesora_field
~~~~~~~~~~~~~~~~

Specifies the name of the field in *Avendesora* that holds the encryption 
passcode. It is used along with *avendesora_account*.  This setting is not 
needed if the field name is *Avendesora's* default.


.. _borg_executable:

borg_executable
~~~~~~~~~~~~~~~

The path to the *Borg* executable or the name of the *Borg* executable. By 
default it is simply ``borg``.


.. _check_after_create:

check_after_create
~~~~~~~~~~~~~~~~~~

Whether the archive or repository should be checked after an archive is created.  
May be one of the following: *False*, *True*, ``"latest"``, ``"all"``, or 
``"all in repository"``.  If *False*, not checking is performed. If 
``"latest"``, only the just created archive is checked.  If *True* or ``"all"``, 
all archives associated with the current configuration are checked.  Finally, if 
``"all in repository"``, all the archives contained in the repository are 
checked.  In all cases checked are performed on the repository and the archive 
or archives selected, but in none of the cases is data integrity verification 
performed.  Regardless, the checking can be quite slow if ``"all"`` or ``"all in 
repository"`` are used.


.. _configurations:

configurations
~~~~~~~~~~~~~~

The list of available *Emborg* configurations.  To be usable the name of 
a configuration must be in this list and there must be a file of the same name 
in the ``~/.config/emborg`` directory.


.. _default_configuration:

default_configuration
~~~~~~~~~~~~~~~~~~~~~

The name of the configuration to use if one is not specified on the command 
line.


.. _default_mount_point:

default_mount_point
~~~~~~~~~~~~~~~~~~~

The path to a directory that should be used if one is not specified on the 
:ref:`mount command <mount>` or :ref:`umount command <umount>` commands.  When 
set the mount point directory becomes optional on these commands. You should 
choose a directory that itself is not subject to being backed up to avoid 
creating a loop. For example, you might consider something in /tmp::

    _default_mount_point = '/tmp/emborg'


.. _encryption:

encryption
~~~~~~~~~~

The encryption mode that is used when first creating the repository. Common 
values are ``"none"``, ``"authenticated"``, ``"repokey"``, and ``"keyfile"``.  
The repository is encrypted if you choose ``"repokey"`` or ``"keyfile"``. In 
either case the passphrase you provide does not encrypt repository. Rather the 
repository is encrypted using a key that is randomly generated by *Borg*.  You 
passphrase encrypts the key.  Thus, to restore your files you will need both the 
key and the passphrase.  With `"repokey"`` your key is copied to the repository, 
so ``"repokey"`` should only be used with trusted repositories. Use 
``"keyfile"`` if the remote repository is not trusted. It does not copy the key 
to the repository, meaning that it is extremely important for you export the key 
using 'borg key export' and keep a copy in a safe place along with the 
passphrase.


.. _excludes:

excludes
~~~~~~~~

A list of files or directories to exclude from the backups.  Typical value might 
be::

    excludes = '''
        ~/tmp
        ~/.local
        ~/.cache
        ~/.mozilla
        ~/.thunderbird
        ~/.config/google-chrome*
        ~/.config/libreoffice
        ~/**/__pycache__
        ~/**/*.pyc
        ~/**/.*.swp
        ~/**/.*.swo
    '''.split()

In this example ``.split()`` was used to create the list, which would not be 
appropriate if one or more of your excludes contained spaces.


.. _exclude_from:

exclude_from
~~~~~~~~~~~~

An alternative to :ref:`excludes`.  You can list your excludes in one or more 
files, one per line, and then specify the file or files using the *exclude_from* 
setting.  The value of *exclude_from* may either be a string or a list of 
strings. The string or strings would be the paths to the file or files that 
contain the list of files or directories to exclude. If given as relative paths, 
they are relative to the ``~/.config/emborg`` directory.


.. _include:

include
~~~~~~~

Can be a string or a list of strings. Each string specifies a path to a file.  
The contents of that file are read into *Emborg*.


.. _must_exist:

must_exist
~~~~~~~~~~

Can be a string or a list of strings. The strings specify paths to files that 
must exist before :ref:`create command <create>` can be run.  This is used to 
assure that relevant file systems are mounted before making backups of their 
files.


.. _needs_ssh_agent:

needs_ssh_agent
~~~~~~~~~~~~~~~

A boolean. If true, *Emborg* will issue an error message and refuse to run if an 
SSH agent is not available.


.. _notifier:

notifier
~~~~~~~~

A string that specifies the command used to interactively notify the user of an 
issue. A typical value is::

    notifier = 'notify-send -u normal {prog_name} "{msg}"'

Any of the following names may be embedded in braces and included in the string.  
They will be replaced by their value:

    msg: The message for the user.
    hostname: The host name of the system that *Emborg* is running on.
    user_name: The user name of the person that started *Emborg*
    prog_name: The name of the *Emborg* program.

The notifier is only used if the command is not running from a TTY.


.. _notify:

notify
~~~~~~

A string that contains one or more email addresses separated with spaces.  If 
specified, an email will be sent to each of the addresses to notify them of any 
problems that occurred while running *Emborg*.

The email is only sent if the command is not running from a TTY.


.. _passcommand:

passcommand
~~~~~~~~~~~

A string that specifies a command to be run by *BORG* to determine the pass 
phrase for the encryption key. The standard out of this command is used as the 
pass phrase.  This string is passed to *Borg*, which executes the command.

This is used as an alternative to :ref:`passphrase` when it is desirable to keep 
the passphrase out of your configuration file.

.. _passphrase:

passphrase
~~~~~~~~~~

A string that specifies the pass phrase for the encryption key.  This string is 
passed to *Borg*.  When specifying a pass phrase you should be careful to assure 
that the configuration file that contains is only readable by the user and 
nobody else.


.. _prune_after_create:

prune_after_create
~~~~~~~~~~~~~~~~~~

A boolean. If true the :ref:`prune command <prune>` is run after creating an 
archive.

.. _repository:

repository
~~~~~~~~~~

The destination for the backups. A typical value might be::

    repository = 'archives:/mnt/backups/{host_name}-{user_name}-{config_name}'

where in this example 'archives' is the hostname and /mnt/backups is the 
absolute path to the directory that is to contain your Borg repositories, 
and {host_name}-{user_name}-{config_name} is the directory to contain this 
repository.  For a local repository you would use something like this::

    repository = '/mnt/backups/{host_name}-{user_name}-{config_name}'

These examples assume that */mnt/backups* contains many independent 
repositories, and that each repository contains the files associated with 
a single backup configuration.  Borg allows you to make a repository the target 
of many backup configurations, and in this way you can further benefit from its 
ability to de-duplicate files.  In this case you might want to use a less 
granular name for your repository.  For example, a particular user could use 
a single repository for all their configurations on all their hosts using::

    repository = '/mnt/backups/{user_name}'

In this case you should specify the :ref:`prefix` setting, described next, to 
allow the archives created by each backup configuration to be distinguished.


.. _run_after_backup:

run_after_backup
~~~~~~~~~~~~~~~~

Can be a string or a list of strings. Each string specifies a command that is to 
be run after the :ref:`create` command completes. These commands often recreate 
useful files that were deleted by the :ref:`run_before_backup` commands.


.. _run_before_backup:

run_before_backup
~~~~~~~~~~~~~~~~~

Can be a string or a list of strings. Each string specifies a command that is to 
be run before the :ref:`create` command starts the backup. These commands often 
delete large files that can be easily recreated from those files that are backed 
up.


.. _src_dirs:

src_dirs
~~~~~~~~

A list of strings, each of which specifies a directory to be backed up.


.. _ssh_command:

ssh_command
~~~~~~~~~~~

A string that contains the command to be used for SSH. The default is ``"ssh"``.  
This can be used to specify SSH options.


.. _verbose:

verbose
~~~~~~~

A boolean. If true *Borg* is run in verbose mode and the output from *Borg* is 
output by *Emborg*.


Borg Settings
-------------

These settings control the behavior of *Borg*. Detailed descriptions can be 
found in the `Borg documentation 
<https://borgbackup.readthedocs.io/en/stable/usage/general.html>`_.

.. _append_only:

append_only
~~~~~~~~~~~

Create an append-only mode repository.


.. _compression:

compression
~~~~~~~~~~~

The name of the desired compression algorithm.


.. _exclude_caches:

exclude_caches
~~~~~~~~~~~~~~

Exclude directories that contain a CACHEDIR.TAG file.


.. _exclude_if_present:

exclude_if_present
~~~~~~~~~~~~~~~~~~

exclude directories that are tagged by containing a filesystem object with the given NAME


.. _lock_wait:

lock_wait
~~~~~~~~~

Wait at most SECONDS for acquiring a repository/cache lock (default: 1)


.. _keep_within:

keep_within
~~~~~~~~~~~

Keep all archives within this time interval.


.. _keep_last:

keep_last
~~~~~~~~~

Number of the most recent archives to keep.


.. _keep_minutely:

keep_minutely
~~~~~~~~~~~~~

Number of minutely archives to keep.


.. _keep_hourly:

keep_hourly
~~~~~~~~~~~

Number of hourly archives to keep.


.. _keep_daily:

keep_daily
~~~~~~~~~~

Number of daily archives to keep.


.. _keep_weekly:

keep_weekly
~~~~~~~~~~~

Number of weekly archives to keep.


.. _keep_monthly:

keep_monthly
~~~~~~~~~~~~

Number of monthly archives to keep.


.. _keep_yearly:

keep_yearly
~~~~~~~~~~~

Number of yearly archives to keep.


.. _one_file_system:

one_file_system
~~~~~~~~~~~~~~~

Stay in the same file system and do not store mount points of other file 
systems.


.. _prefix:

prefix
~~~~~~

Only consider archive names starting with this prefix.
For more, see :ref:`archive`.


.. _remote_path:

remote_path
~~~~~~~~~~~

Name of *Borg* executable on remote platform.


.. _remote_ratelimit:

remote_ratelimit
~~~~~~~~~~~~~~~~

Set remote network upload rate limit in KiB/s (default: 0=unlimited).


.. _umask:

umask
~~~~~

Set umask to M (local and remote, default: 0o077).
