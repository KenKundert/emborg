.. _configuring_emborg:

Configuring
===========

Typically the settings files go in the default location for configuration files 
on your system.  On Linux systems, that location is ~/.config/emborg.  Other 
systems use more awkward locations, so while *Emborg* creates initial versions 
in the default location, you are free to move them to ~/.config/emborg if you 
prefer.  *Emborg* always checks for the files in ~/.config/emborg if it exists 
before looking in the default location for your system.

You need a shared settings file and then one file for each backup configuration 
you need.  Except for :ref:`configurations` and :ref:`default_configuration` any 
setting may be placed in either the shared file or the configuration specific 
file.  If a setting is found in both files, the version in the configuration 
specific file dominates.

You can get a complete list of available configuration settings by running:

.. code-block:: bash

    $ emborg settings --available


.. _shared_settings:

Shared Settings
---------------

Shared settings go in ~/.config/emborg/settings.  This is a Python file that 
contains values shared by all of your configurations.  It might look like the 
following:

.. code-block:: python

    default_configuration = 'home'        # default backup configuration
    configurations = 'home websites'      # available backup configurations
    avendesora_account = 'borg-backup'    # Avendesora account name (holds passphrase for encryption key)
    passphrase = None                     # passphrase to use (if specified, Avendesora is not used)
    encryption = 'keyfile'                # encryption method
    prune_after_create = True             # run prune as the last step of an archive creation
    check_after_create = 'latest'         # run check as the last step of an archive creation
    #notify = "me@mydomain.com"            # email address to notify when things go wrong
    notifier = 'notify-send -u normal {prog_name} "{msg}"'
                                          # program used to send realtime notifications
                                          # generally you use notify or notifier, but not both
                                          # use notifier for interactive backups 
                                          # and notify for scheduled backups
                                          # notification program
    upload_ratelimit = 2000               # bandwidth limit in kbps
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
readable by others (chmod 600 settings).  Alternatively, you can use 
:ref:`passcommand`, which runs a command that returns your pass phrase.  
Finally, you can use `Avendesora <https://avendesora.readthedocs.io>`_ to 
securely hold your key by specifying the Avendesora account name of the key to 
:ref:`avendesora_account`.

This example assumes that there is one backup configuration per repository. You 
can instead have more than one configurations share a single repository by 
adjusting :ref:`repository` and adding :ref:`glob_archives` like so:

.. code-block:: python

    repository = 'archives:/mnt/backups/{host_name}/{user_name}'
    glob_archives = '{config_name}-*'

In this case several backup configurations would deposit archives into a single 
directory, allowing them to reduce the total space required to hold the archives 
if there are shared files between the configurations.  The :ref:`glob_archives` 
setting is required to allow each backup configuration to recognize its own 
archives.  All archive names that match the glob string associate with this 
configuration.


.. _individual_configurations:

Configurations
--------------

Each backup configuration must have a settings file in ~/.config/emborg. The 
name of the file is the name of the backup configuration.  It might look like 
the following:

.. code-block:: python

    src_dirs = '~'           # absolute paths to directories to be backed up
    excludes = """
        ~/tmp
        ~/**/.hg
        ~/**/.git
        ~/**/*.pyc
        ~/**/.*.swp
        ~/**/.*.swo
    """                      # list of glob strings of files or directories to skip
    one_file_system = False  # okay to traverse filesystems

    # commands to be run before and after backups (run from working directory)
    run_before_first_backup = """
        # remove the detritus before backing up
        ~/bin/clean-home >& {log_dir}/clean-home.log
    """
    run_after_last_backup = """
        # rebuild my documentation, it was deleted by clean-home
        ~/bin/rebuild-documentation > /dev/null
    """

    # if set, this file or these files must exist or backups will quit with an error
    must_exist = '~/doc/thesis'

String values may incorporate other string valued settings. Use braces to 
interpolate another setting. In addition, you may interpolate the configuration 
name ('config_name'), the host name ('host_name'), the user name ('user_name'), 
Emborg's program name ('prog_name'), your home directory ('home_dir'), the 
configuration directory ('config_dir') or the output directory ('log_dir').  An 
example of this is shown in both :ref:`repository` and :ref:`archive` above.  
Doubling up the braces acts to escape them.  In this way you gain access to 
*Borg* placeholders. :ref:`archive` shows an example of that.  Interpolation is 
not performed on any setting whose name is given in :ref:`do_not_expand`.

Settings that take lists of strings can be specified as a single multi-line 
string where one item is given per line.  Lines that begin with # are ignored, 
as are empty lines.  For example:

.. code-block:: python

    excludes = """
        # these directories would be problematic if backed up
        /dev
        /proc

        # these directories contain largely derived files which can be recreated
        /run
        /sys
        /tmp
        /var
    """


.. _paths:

Paths
-----

When *Borg* places files into a repository, it always uses relative paths.  
However, you may specify them either using relative paths or absolute paths.
*Borg* starts backing up from the recursion roots. These are directories that 
you specify to :ref:`src_dirs` or using the ``R`` key in :ref:`patterns` or 
:ref:`patterns_from`.  Within a recursion root you can specify particular paths 
to exclude and within those you can specify particular files to include. This is 
done using :ref:`excludes` and :ref:`exclude_from` and using the path keys 
(``+``, ``-``, ``!``) in :ref:`patterns` and :ref:`patterns_from`.  When you use 
a relative path to specify a recursion root then you should also use relative 
paths for its include and exclude paths. Similarly, if you use an absolute path 
for the recursion root then you should also use absolute paths for its include 
and exclude paths. *Borg* is okay with you having some recursion roots specified 
with relative paths and some with absolute paths, but this confuses *Emborg* 
when it comes time to extract or restore files from your repository. With 
*Emborg*, all of your recursive roots must either be specified using relative 
paths or they must all be specified with absolute paths.

If you specify absolute paths, *Borg* converts them to relative paths as it 
inserts them into the repository by stripping off the leading ``/`` from the 
path.  If you specify relative paths, it inserts them as is.  When using *Borg* 
directly, the relative paths would be relative to the directory where *borg 
create* is invoked. For this reason, *borg create* must always be invoked from 
the same directory when using relative paths. To make this work, *Emborg* 
internally changes to :ref:`working_dir` before running *borg create*.  Thus, if 
you choose to use relative paths, you should also specify :ref:`working_dir`, 
which should be specified with an absolute path.  For example:

.. code-block:: python

    working_dir = '~'
    src_dirs = '.'
    excludes = """
        .cache
        *~
    """

If you do not specify :ref:`working_dir`, it defaults to ``/``.

Other than paths to include files, all relative paths specified in your 
configuration are relative to :ref:`working_dir`.  This can be confusing, so it 
is recommended that all paths in your configuration, other than those being 
passed directly to *Borg* should be given using absolute paths.  This includes 
settings such as :ref:`default_mount_point`, :ref:`must_exist`, 
:ref:`patterns_from`, and :ref:`exclude_from`.

Paths specified directly to *Emborg* are processed and any leading tildes 
(``~``) are expanded to the appropriate user's home directory. However, paths 
specified in :ref:`exclude_from` and :ref:`patterns_from` files are processed 
directly by *Borg*, which does not expand tildes to a user's home directory.


.. _includes:

Includes
--------

Any settings file may include the contents of another file by using
:ref:`include`.  You may either specify a single include file as a string or 
a collection as a list of strings or a multi-line string. For example:

.. code-block:: python

    include = 'file-to-include'

or:

.. code-block:: python

    include = """
        first-file-to-include
        second-file-to-include
    """

If you specify a relative path for an include file, it it relative to the file 
that includes it.


.. _composite_configurations:

Composite Configurations
------------------------

It is possible to define composite configurations that allow you to run several 
configurations at once.  This might be useful if you want to backup to more than 
one repository for redundancy.  Or perhaps you have files that benefit from 
different prune schedules.

As an example, consider having three configurations that you would like to run 
all at once. You can specify these configurations as follows:

.. code-block:: python

    configurations = 'home lamp data all=home,lamp,data'

In this case *home*, *lamp*, and *data* are simple configurations and *all* is 
a composite configuration.  *home*, *lamp*, and *data* would have configuration 
files whereas *all* would not.  The composite configuration should be specified 
without spaces.

You can run a specific configuration with:

.. code-block:: bash

    $ emborg -c home extract ~/bin

You can run all three configurations with:

.. code-block:: bash

    $ emborg -c all create

Only certain commands support composite configurations, and if a command does 
support composite configurations it may either apply each subconfig in sequence, 
or only the first subconfig.

==========  ===============================
Command     Response to Composite Config
==========  ===============================
borg        error
breaklock   error
check       run on each subconfig
configs     does not use any configurations
create      run on each subconfig
delete      error
diff        error
due         run on each subconfig
extract     run only on first subconfig
help        does not use any configurations
info        run on each subconfig
initialize  run on each subconfig
list        run only on first subconfig
log         run on each subconfig
manifest    run only on first subconfig
mount       run only on first subconfig
prune       run on each subconfig
restore     run only on first subconfig
settings    error
umount      run only on first subconfig
version     does not use any configurations
==========  ===============================


.. _patterns_intro:

Patterns
--------

Patterns are a relatively new feature of *Borg*. They are an alternate way of 
specifying which files are backed up, and which are not.  Patterns can be 
specified in conjunction with, or instead of, :ref:`src_dirs` and 
:ref:`excludes`.  One powerful feature of patterns is that they allow you to 
specify that a directory or file should be backed up even if it is contained 
within a directory that is being excluded.

An example that uses :ref:`patterns` in lieu of :ref:`src_dirs` and 
:ref:`excludes` is:

.. code-block:: python

    patterns = """
        R /
        + /home/susan
        - /home
        - /dev
        - /opt
        - /proc
        - /run
        - /sys
        - /tmp
        - /var
    """

In this example, ``R`` specifies a root, which would otherwise be specified to 
:ref:`src_dirs`.  ``+`` specifies path that should be included in the backups 
and ``-`` specifies a path that should be excluded.  With this example, Susan's 
home directory is included while all other home directories are not. In cases 
such as this, the subdirectory to include must be specified before the directory 
that contains it is excluded.  This is a relatively simple example, additional 
features are described in the `Borg patterns documentation 
<https://borgbackup.readthedocs.io/en/stable/usage/help.html>`_.


.. _retention:

Archive Retention
-----------------

You use the retention limits (the ``keep_X`` settings) to specify how long to 
keep archives after they have been created.  A good description of the use of 
these settings can be found on the `Borg Prune Command 
<https://borgbackup.readthedocs.io/en/stable/usage/prune.html>`_ page.

Generally you want to thin the archives out more and more as they age.  When 
choosing your retention limits you need to consider the nature of the files you 
are archiving.  Specifically you need to consider how often the files change, 
whether you would want to recover prior versions of the files you keep and if so 
how many prior versions are of interest, and how long precious files may be 
missing or damaged before you notice that they need to be restored.

If files are changing all the time, long high retention limits result in high 
storage requirements.  If you want to make sure you retain the latest version of 
a file but you do not need prior versions, then you can reduce your retention 
limits to reduce your storage requirements.  For example, consider a directory 
of log files.  Log files generally change all the time, but they also tend to be 
cumulative, meaning that the latest file contains the information contained in 
prior versions of the same file, so keeping those prior versions is of low 
value.  In this situation using “*keep_last N*” where *N* is small is a good 
approach.

Now consider a directory of files that should be kept forever, such as family 
photos or legal documents.  The loss of these files due to disk corruption or 
accidental deletion might not be noticed for years.  In this case you would want 
to specify “*keep_yearly N*” where *N* is large.  These files never change, so 
the de-duplication feature of *Borg* avoids growth in storage requirements 
despite high retention limits.

You cannot specify retention limits on a per file or per directory basis within 
a single configuration.  Instead, if you feel it is necessary, you would create 
individual configurations for files with different retention needs.  For 
example, as a system administrator you might want to create separate 
configurations for operating system files, which tend to need low retention 
limits, and users home directories, which benefit from longer retention limits.

Remember that your retention limits are not enforced until you run the 
:ref:`prune command <prune>`.  Furthermore, with *Borg 1.2* and later, after 
running the *prune command*, the disk space is not reclaimed until you run the 
:ref:`compact command <compact>`.  You can automate pruning and compaction using 
the :ref:`prune_after_create` and :ref:`compact_after_delete` settings.


.. _confirming_configuration:

Confirming Your Configuration
-----------------------------

Once you have specified your configuration you should carefully check it to make 
sure you are backing up the files you need and not backing up the files you 
don't need.  It is important to do this in the beginning, otherwise you might 
find your self with a bloated repository that does not contain the files you 
require.

There are a number of ways that *Emborg* can help you check your work.

1. You can run ``emborg settings`` to see the values used by *Emborg* for all 
   settings.

2. You can use *Borg*'s ``--dry-run`` option to perform a practice run and see 
   what will happen.  For example:

   .. code-block:: bash

       $ emborg --dry-run create --list

   will show you all of the files that are to be backed up and which of those 
   files have changed since the last time you created an archive.

3. After running *Emborg* you can run ``emborg log`` to see what *Emborg* did in 
   detail and what it asked *Borg* to do.  The log contains the full *Borg* 
   command invocation and *Borg*'s response.

4. Once you have created your repository and created your first archive, you can 
   use the ``--sort-by-size`` option of the :ref:`manifest command <manifest>` 
   to find the largest files that were copied into the repository.  If they are 
   not needed, you can add them to your exclude list, delete the archive, and 
   then recreate the archive, this time without the large unnecessary files.


.. _emborg_settings:

Emborg Settings
---------------

These settings control the behavior of *Emborg*.


.. _archive:

archive
~~~~~~~

*archive* is a template that specifies the name of each archive.  A typical 
value might be:

.. code-block:: python

    archive = '{config_name}-{{now}}'

*Emborg* examines the string for names within a single brace-pair and replaces 
them with the value specified by the name. Names within double-brace pairs are 
interpreted by *Borg*.

More than one backup configuration can share the same repository.  This allows 
*Borg*’s de-duplication feature to work across all configurations, resulting in 
less total space needed for the combined set of all your archives.  In this case 
you must also set the :ref:`glob_archives <glob_archives>` setting so that each 
backup configuration can recognize its own archives.  It is used by the 
:ref:`check`, :ref:`delete`, :ref:`info`, :ref:`list`, :ref:`mount`, and 
:ref:`prune` commands to filter out archives not associated with the desired 
backup configuration.

The *archive* setting should include *{{now}}* so each archive has a unique 
name, however you can customize how *now* is expanded.  For example, you can 
reduce the length of the timestamp using:

.. code-block:: python

    archive = '{host_name}-{{now:%Y%m%d}}'

However, you should be aware that by including only the date in the archive name 
rather than the full timestamp, you are limiting yourself to creating one 
archive per day.  A second archive created on the same day simply writes over 
the previous archive.


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
May be one of the following: *False*, *True*, ``"latest"``, ``"all"``, or ``"all 
in repository"``.  If *False*, no checking is performed. If ``"latest"``, only 
the archive just created is checked.  If *True* or ``"all"``, all archives 
associated with the current configuration are checked.  Finally, if ``"all in 
repository"``, all the archives contained in the repository are checked, 
including those associated with other archives.  In all cases checks are 
performed on the repository and the archive or archives selected, but in none of 
the cases is data integrity verification performed.  To check the integrity of 
the data you must explicitly run the :ref:`check command <check>`.  Regardless, 
the checking can be quite slow if ``"all"`` or ``"all in repository"`` are used.


.. _colorscheme:

colorscheme
~~~~~~~~~~~

A few commands colorize the text to convey extra information. You can optimize 
the tints of those colors to make them more visible and attractive.  
*colorscheme* should be set to "none", "light", or "dark".  With "none" the text 
is not colored.  In general it is best to use the "light" colorscheme on dark 
backgrounds and the "dark" colorscheme on light backgrounds.


.. _compact_after_delete:

compact_after_delete
~~~~~~~~~~~~~~~~~~~~

If True, the :ref:`compact command <compact>` is run after deleting an archive 
or pruning a repository.

.. note::

    This is an important setting if you are using *Borg 1.2* or later.  You 
    should either set this true or manage the compaction in another way.  
    Setting it true results in slightly slower backups.  The alternative is 
    generally to configure *cron* or *anacron* to run the *compact* command 
    routinely for you.

    Do not use this setting if you are not using *Borg* version 1.2 or later.


.. _configurations:

configurations
~~~~~~~~~~~~~~

The list of available *Emborg* configurations.  To be usable the name of 
a configuration must be in this list and there must be a file of the same name 
in the ``~/.config/emborg`` directory.

The value may be specified as a list of strings or just as a string. If 
specified as a string, it is split on white space to form the list.


.. _cronhub_url:

cronhub_url
~~~~~~~~~~~

This setting specifies the URL to use for `cronhub.io <https://cronhub.io>`_.
Normally it is not needed.  If not specified ``https://cronhub.io`` is used.  
You only need to specify the URL in special cases.


.. _cronhub_uuid:

cronhub_uuid
~~~~~~~~~~~~

If this setting is provided, *Emborg* notifies `cronhub.io 
<https://cronhub.io>`_ when the archive is being created and whether the 
creation was successful.  The value of the setting should be a UUID (a 32 digit 
hexadecimal number that contains 4 dashes).  If given, this setting should be 
specified on an individual configuration.  For example:

.. code-block:: python

    cronhub_uuid = '51cb35d8-2975-110b-67a7-11b65d432027'


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
creating a loop. For example, you might consider something in /tmp:

.. code-block:: python

    default_mount_point = '/tmp/emborg'


.. _do_not_expand:

do_not_expand
~~~~~~~~~~~~~

All settings that are specified as strings or lists of strings may contain 
placeholders that are expanded before use. The placeholder is replaced by the 
value it names.  For example, in:

.. code-block:: python

    archive = '{host_name}-{{now}}'

*host_name* is a placeholder that is replaced by the host name of your computer 
before it is used (*now* is escaped using double braces and so does not act as 
a placeholder for *Emborg*.

*do_not_expand* is a list of names for settings that should not undergo 
placeholder replacement.  The value may be specified as a list of strings or 
just as a string. If specified as a string, it is split on white space to form 
the list.

.. _encoding:

encoding
~~~~~~~~

The encoding used when communicating with Borg. The default is utf-8, which is 
generally suitable for Linux systems.


.. _encryption:

encryption
~~~~~~~~~~

The encryption mode that is used when first creating the repository.  Common 
values are ``none``, ``authenticated``, ``repokey``, and ``keyfile``.  The 
repository is encrypted if you choose ``repokey`` or ``keyfile``. In either case 
the passphrase you provide does not encrypt repository.  Rather the repository 
is encrypted using a key that is randomly generated by *Borg*.  You passphrase 
encrypts the key.  Thus, to restore your files you will need both the key and 
the passphrase.  With ``repokey`` your key is copied to the repository, so 
``repokey`` should only be used with trusted repositories. Use ``keyfile`` if 
the remote repository is not trusted. It does not copy the key to the 
repository, meaning that it is extremely important for you export the key using 
'borg key export' and keep a copy in a safe place along with the passphrase.

Once encrypted, a passphrase is needed to access the repository.  There are 
a variety of ways to provide it.  *Borg* itself uses the *BORG_PASSPHRASE*, 
*BORG_PASSPHRASE_FD*, and *BORG_COMMAND* environment variables if set.  
*BORG_PASSPHRASE* contains the passphrase, or *BORG_PASSPHRASE_FD* is a file 
descriptor that provides the passphrase, or *BORG_COMMAND* contains a command 
that generates the passphrase.  If none of those are set, *Emborg* looks to its 
own settings.  If either :ref:`passphrase` or :ref:`passcommand` are set, they 
are used.  If neither are set, *Emborg* uses :ref:`avendesora_account` if set.  
Otherwise no passphrase is available and the command fails if the repository is 
encrypted.


.. _excludes:

excludes
~~~~~~~~

A list of files or directories to exclude from the backups.  Typical value might 
be:

.. code-block:: python

    excludes = """
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
    """

The value can either be specified as a list of strings or as a multi-line string 
with one exclude per line.

*Emborg* supports the same exclude patterns that `Borg 
<https://borgbackup.readthedocs.io/en/stable/usage/help.html>`_ itself supports. 

When specifying paths to excludes, the paths may be relative or absolute. When 
relative, they are taken to be relative to :ref:`working_dir`.


.. _exclude_from:

exclude_from
~~~~~~~~~~~~

An alternative to :ref:`excludes`.  You can list your excludes in one or more 
files, one per line, and then specify the file or files using the *exclude_from* 
setting:

.. code-block:: python

    exclude_from = '{config_dir}/excludes'

The value of *exclude_from* may either be a multi-line string, one file per 
line, or a list of strings. The string or strings would be the paths to the file 
or files that contain the list of files or directories to exclude. If given as 
relative paths, they are relative to :ref:`working_dir`.  These files are 
processed directly by *Borg*, which does not allow ``~`` to represent users' 
home directories, unlike the patterns specified using :ref:`patterns`.


.. _healthchecks_url:

healthchecks_url
~~~~~~~~~~~~~~~~

This setting specifies the URL to use for `healthchecks.io 
<https://healthchecks.io>`_.  Normally it is not needed.  If not specified 
``https://.hc-ping.com`` is used.  You only need to specify the URL in special 
cases.


.. _healthchecks_uuid:

healthchecks_uuid
~~~~~~~~~~~~~~~~~

If this setting is provided, *Emborg* notifies `healthchecks.io 
<https://healthchecks.io>`_ when the archive is being created and whether the 
creation was successful.  The value of the setting should be a UUID (a 32 digit 
hexadecimal number that contains 4 dashes).  If given, this setting should be 
specified on an individual configuration.  For example:

.. code-block:: python

    healthchecks_uuid = '51cb35d8-2975-110b-67a7-11b65d432027'


.. _include:

include
~~~~~~~

Can be a string or a list of strings. Each string specifies a path to a file.  
The contents of that file are read into *Emborg*.  If the path is relative, it 
is relative to the file that includes it.


.. _manage_diffs_cmd:

manage_diffs_cmd
~~~~~~~~~~~~~~~~

Command to use to perform interactive file and directory comparisons using the 
``--interactive`` option to the :ref:`compare command <compare>`.  The command 
may be specified in the form of a string or a list of strings.  If a string, it 
may contain the literal text ``{archive_path}`` and ``{local_path}``, which are 
replaced by the two files or directories to be compared.  If not, then the paths 
are simply appended to the end of the command as specified.  Suitable commands 
for use in this setting include `Vim <https://www.vim.org>`_ with the `DirDiff 
<https://www.vim.org/scripts/script.php?script_id=102>`_  plugin, `Meld 
<https://meldmerge.org>`_, and presumably others such as *DiffMerge*, *Kompare*, 
*Diffuse*, *KDiff3*, etc.  If you are a *Vim* user, another alternative is 
`vdiff <https://github.com/KenKundert/vdiff>`_, which provides a more 
streamlined interface to *Vim/DirDiff*.  Here are examples on how to configure 
*Vim*, *Meld* and *VDiff*:

.. code-block:: python

    manage_diffs_cmd = "meld"
    manage_diffs_cmd = ["meld", "-a"]
    manage_diffs_cmd = "gvim -f -c 'DirDiff {archive_path} {local_path}'"
    manage_diffs_cmd = "vdiff -g"

The :ref:`compare command <compare>` mounts the remote archive, runs the 
specified command and then immediately unmounts the archive.  As such, it is 
important that the command run in the foreground.  By default, *gvim* runs in 
the background.  You can tell this because if run directly in a shell, the shell 
immediately accepts new commands even though *gvim* is still active.  To avoid 
this, the ``-f`` option is added to the *gvim* command line to indicate it 
should run in the foreground.  Without this, you will see an error from 
*fusermount* indicating ‘Device or resource busy’.  If you get this message, you 
will have to close the editor and manually un-mount the archive.


.. _manifest_default_format:

manifest_default_format
~~~~~~~~~~~~~~~~~~~~~~~

A string that specifies the name of the default format.  The name must be a key 
in :ref:`manifest_formats`.  If not specified, ``short`` is used.


.. _manifest_formats:

manifest_formats
~~~~~~~~~~~~~~~~

A dictionary that defines how the output of the manifest command is to be 
formatted.  The default value for *manifest_formats* is:

.. code-block:: python

        manifest_formats = dict(
            name = "{path}",
            short = "{path}{Type}",
            date = "{mtime} {path}{Type}",
            size = "{size:8} {path}{Type}",
            si = "{Size:6.2} {path}{Type}",
            owner = "{user:8} {path}{Type}",
            group = "{group:8} {path}{Type}",
            long = '{mode:10} {user:6} {group:6} {size:8} {mtime} {path}{extra}',
        )
        manifest_default_format = 'short'

Notice that 8 formats are defined:

    :name: used when ``--name-only`` is specified.
    :short: used by when ``--short`` is specified and when sorting by name.
    :date: used by default when sorting by date.
    :size: size in bytes (fixed format).
    :si: size in bytes (SI format), used by default when sorting by size.
    :owner: used by default when sorting by owner.
    :group: used by default when sorting by group.
    :long: used when ``--long`` is specified.

Your *manifest_formats* need not define all or even any of these formats.
The above example shows the formats that are predefined in *Emborg*. You do not 
need to specify them again.  Anything you specify will override the predefined 
versions, and you can add additional formats.

The formats may contain the fields supported by the `Borg list command 
<https://borgbackup.readthedocs.io/en/stable/usage/list.html#borg-list>`_.  In 
addition, Emborg provides some variants:

*MTime*, *CTime*, *ATime*:
   The *Borg* *mtime*, *ctime*, and *atime* fields are simple strings, these 
   variants are `Arrow objects 
   <https://arrow.readthedocs.io/en/latest/#supported-tokens>`_ that support 
   formatting options.  For example:

   .. code-block:: python

        date = "{MTime:ddd YYYY-MM-DD HH:mm:ss} {path}{Type}",

*Size*, *CSize*, *DSize*, *DCSize*:
   The *Borg* *size*, *csize*, *dsize* and *dctime* fields are simple integers, 
   these variants are `QuantiPhy objects 
   <https://quantiphy.readthedocs.io/en/stable/user.html#string-formatting>`_ 
   that support formatting options.  For example:

   .. code-block:: python

        size = "{Size:5.2r} {path}{Type}",
        size = "{Size:7.2b} {path}{Type}",

*Type*:
   Displays ``/`` for directories, ``@`` for symbolic links, and ``|`` for named 
   pipes.

*QuantiPhy* objects allow you to format the size using SI scale factors (K, Ki, 
M, Mi, etc.). *Arrow* objects allow you to format the date and time in a wide 
variety of ways.  Any use of *QuantiPhy* or *Arrow* can slow long listings 
considerably.

The fields support `Python format strings 
<https://docs.python.org/3/library/string.html#formatstrings>`_, which allows 
you to specify how they are to be formatted.  Anything outside a field is copied 
literally.


.. _must_exist:

must_exist
~~~~~~~~~~

Specify paths to files that must exist before :ref:`create command <create>` can 
be run.  This is used to assure that relevant file systems are mounted before 
making backups of their files.

May be specified as a list of strings or as a multi-line string with one path 
per line.


.. _needs_ssh_agent:

needs_ssh_agent
~~~~~~~~~~~~~~~

A Boolean. If true, *Emborg* will issue an error message and refuse to run if an 
SSH agent is not available.


.. _notifier:

notifier
~~~~~~~~

A string that specifies the command used to interactively notify the user of an 
issue. A typical value is:

.. code-block:: python

    notifier = 'notify-send -u critical {prog_name} "{msg}"'

Any of the following names may be embedded in braces and included in the string.  
They will be replaced by their value:

 |  *msg*: The message for the user.
 |  *hostname*: The host name of the system that *Emborg* is running on.
 |  *user_name*: The user name of the person that started *Emborg*
 |  *prog_name*: The name of the *Emborg* program.

The notifier is only used if the command is not running from a TTY.

Use of *notifier* requires that you have a notification daemon installed (ex: 
`Dunst <https://wiki.archlinux.org/title/Dunst>`_).  The notification daemon 
provides the *notify-send* command.  If you do not have the *notify-send* 
command, do not set *notifier*.

The *notify* and *notifier* settings operate independently.  You may specify 
none, one, or both.  Generally, one uses just one: *notifier* if you primarily 
use *Emborg* interactively and *notify* if used from cron or anacron.


.. _notify:

notify
~~~~~~

A string that contains one or more email addresses separated with spaces.  If 
specified, an email will be sent to each of the addresses to notify them of any 
problems that occurred while running *Emborg*.

The email is only sent if the command is not running from a TTY.

Use of *notify* requires that you have a mail daemon installed (ex: `PostFix 
<http://www.postfix.org>`_ configured as a null client).  The mail daemon 
provides the *mail* command.  If you do not have the *mail* command, do not set 
*notify*.

The *notify* and *notifier* settings operate independently.  You may specify 
none, one, or both.  Generally, one uses just one: *notifier* if you primarily 
use *Emborg* interactively and *notify* if used from cron or anacron.


.. _passcommand:

passcommand
~~~~~~~~~~~

A string that specifies a command to be run by *BORG* to determine the pass 
phrase for the encryption key. The standard out of this command is used as the 
pass phrase.  This string is passed to *Borg*, which executes the command.

Here is an example of a passcommand that you can use if your GPG agent is 
available when *Emborg* is run. This works if you are running it interactively, 
or in a cron script if you are using `keychain 
<https://www.funtoo.org/Keychain>`_ to provide you access to your GPG agent:

.. code-block:: python

    passcommand = 'gpg -qd /home/user/.store-auth.gpg'

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

A Boolean. If true the :ref:`prune command <prune>` is run after creating an 
archive.


.. _report_diffs_cmd:

report_diffs_cmd
~~~~~~~~~~~~~~~~

Command used to perform file and directory comparisons using the :ref:`compare 
command <compare>`.  The command may be specified in the form of a string or 
a list of strings.  If a string, it may contain the literal text 
``{archive_path}`` and ``{local_path}``, which are replaced by the two files or 
directories to be compared.  If not, then the paths are simply appended to the 
end of the command as specified.  Suitable commands for use in this setting 
include ``diff -r`` the and ``colordiff -r``.  Here are examples of two 
different but equivalent ways of configuring *diff*:

.. code-block:: python

    report_diffs_cmd = "diff -r"
    report_diffs_cmd = "diff -r {archive_path} {local_path}"

You may prefer to use *colordiff*, which is like *diff* but in color:

.. code-block:: python

    report_diffs_cmd = "colordiff -r"


.. _repository:

repository
~~~~~~~~~~

The destination for the backups. A typical value might be:

.. code-block:: python

    repository = 'archives:/mnt/backups/{host_name}-{user_name}-{config_name}'

where in this example 'archives' is the hostname and /mnt/backups is the 
absolute path to the directory that is to contain your Borg repositories, 
and {host_name}-{user_name}-{config_name} is the directory to contain this 
repository.  For a local repository you would use something like this:

.. code-block:: python

    repository = '/mnt/backups/{host_name}-{user_name}-{config_name}'

These examples assume that */mnt/backups* contains many independent 
repositories, and that each repository contains the files associated with 
a single backup configuration.  Borg allows you to make a repository the target 
of more than one backup configuration, and in this way you can further benefit 
from its ability to de-duplicate files.  In this case you might want to use 
a less granular name for your repository.  For example, a particular user could 
use a single repository for all their configurations on all their hosts using:

.. code-block:: python

    repository = '/mnt/backups/{user_name}'

When more than one configuration shares a repository you should specify the 
:ref:`glob_archives` setting so that each configuration can recognize its own 
archives.

A local repository should be specified with an absolute path, and that path 
should not contain a colon (``:``) to avoid confusing the algorithm that 
determines whether the repository is local or remote.


.. _run_after_backup:
.. _run_after_last_backup:

run_after_backup, run_after_last_backup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specifies commands that are to be run after the :ref:`create <create>` command 
successfully completes.  These commands often recreate useful files that were 
deleted by the :ref:`run_before_backup <run_before_backup>` commands.

May be specified as a list of strings or as a multi-line string with one command 
per line (lines that begin with ``#`` are ignored).  If given as a string, 
a shell is used to run the command or commands.  If given as a list of strings, 
a shell is not used, meaning that shell path and variable expansions, 
redirections and pipelines are not available.

The commands specified in *run_after_backup* are run each time an archive is 
created whereas commands specified in *run_after_last_backup* are run only if 
the configuration is run individually or if it is the last run in a composite 
configuration.  For example, imagine a composite configuration *home* that 
consists of two children, *local* and *remote*, and imagine that both are 
configured to run the command *restore* after they are run.  If 
*run_after_backup* is used to specify *restore*, then running ``emborg -c home 
create`` results in *restore* being run twice, after both the *local* and 
*remote* archives are created.  However, if *run_after_last_backup* is used, 
*restore* is only run once, after the *remote* archive is created.  Generally, 
one specifies identical commands to *run_after_last_backup* for each 
configuration in a composite configuration with the intent that the commands 
will be run only once regardless whether the configurations are run individually 
or as a group.

For example, the following runs :ref:`borg space` after each back-up to record 
the size history of your repository:

.. code-block:: python

    run_after_backup = [
        'borg-space -r -m "Repository is now {{size:.2}}." {config_name}'
    ]


.. _run_before_backup:
.. _run_before_first_backup:

run_before_backup, run_before_first_backup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specifies commands that are to be run before the :ref:`create <create>` command 
starts the backup. These commands often delete large files that can be easily 
recreated from those files that are backed up.

May be specified as a list of strings or as a multi-line string with one command 
per line (lines that begin with ``#`` are ignored).  If given as a string, 
a shell is used to run the command or commands.  If given as a list of strings, 
a shell is not used, meaning that shell path and variable expansions, 
redirections and pipelines are not available.

The commands specified in *run_before_backup* are run each time an archive is 
created whereas commands specified in *run_before_first_backup* are run only if 
the configuration is run individually or if it is the first run in a composite 
configuration.  For example, imagine a composite configuration *home* that 
consists of two children, *local* and *remote*, and imagine that both are 
configured to run the command *clean* before they are run.  If 
*run_before_backup* is used to specify *clean*, then running ``emborg -c home 
create`` results in *clean* being run twice, before both the *local* and 
*remote* archives are created.  However, if *run_before_first_backup* is used, 
*clean* is only run once, before the *local* archive is created.  Generally, one 
specifies identical commands to *run_before_first_backup* for each configuration 
in a composite configuration with the intent that the commands will be run only 
once regardless whether the configurations are run individually or as a group.


.. _run_before_borg:
.. _run_after_borg:

run_before_borg, run_after_borg
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specifies commands that are to be run before the first *Borg* command is run or 
after the last one is run.  These can be used, for example, to mount and then 
unmount a remote repository, if such a thing is needed.

May be specified as a list of strings or as a multi-line string with one command 
per line (lines that begin with ``#`` are ignored).  If given as a string, 
a shell is used to run the command or commands.  If given as a list of strings, 
a shell is not used, meaning that shell path and variable expansions, 
redirections and pipelines are not available.


.. _show_progress:

show_progress
~~~~~~~~~~~~~

Show progress when running *Borg*'s *create* command.
You also get this by adding the ``--progress`` command line option to the 
*create* command, but if this option is set True then this command will always 
show the progress.


.. _show_stats:

show_stats
~~~~~~~~~~

Show statistics when running *Borg*'s *create*, *delete* and *prune* commands.
You can always get this by adding the ``--stats`` command line option to the 
appropriate commands, but if this option is set True then these commands will 
always show the statistics.  If the statistics are not requested, they will be 
recorded in the log file rather than being displayed.

Statistics are incompatible with the --dry-run option and will be suppressed 
on trial runs.


.. _src_dirs:

src_dirs
~~~~~~~~

A list of strings, each of which specifies a directory to be backed up.  May be 
specified as a list of strings or as a multi-line string with one source 
directory per line.

When specifying the paths to the source directories, the paths may be relative 
or absolute.  When relative, they are taken to be relative to 
:ref:`working_dir`.


.. _ssh_command:

ssh_command
~~~~~~~~~~~

A string that contains the command to be used for SSH. The default is ``"ssh"``.  
This can be used to specify SSH options.


.. _verbose:

verbose
~~~~~~~

A Boolean. If true *Borg* is run in verbose mode and the output from *Borg* is 
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


.. _chunker_params:

chunker_params
~~~~~~~~~~~~~~

Parameters used by the chunker command.
More information is available from `chunker_params Borg documentation
<https://borgbackup.readthedocs.io/en/stable/usage/notes.html#chunker-params>`_.


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

Exclude directories that are tagged by containing a filesystem object with the given NAME


.. _exclude_nodump:

exclude_nodump
~~~~~~~~~~~~~~

Exclude files flagged NODUMP.


.. _glob_archives:

glob_archives
~~~~~~~~~~~~~

A glob string that a backup configuration uses to recognize its archives when 
more than one configuration is sharing the same repository.  A glob string is 
a string that is expected to match the name of the archives.  It must contain at 
least one asterisk (``*``).  Each asterisk will match any number of contiguous 
characters.  For example, a *glob_archives* setting of ``home-*`` will match 
``home-2022-10-23T19:11:04``.

*glob_archives* is required if you save the archives of multiple backup 
configurations to the same repository.  Otherwise it is not needed.  It is used 
by the :ref:`check`, :ref:`delete`, :ref:`info`, :ref:`list`, :ref:`mount`, and 
:ref:`prune` commands to filter out archives not associated with the desired 
backup configuration.


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


.. _patterns:

patterns
~~~~~~~~

A list of files or directories to exclude from the backups.  Typical value might 
be:

.. code-block:: python

    patterns = """
        R /
        - /home/*/.cache
        - /home/*/Downloads

        # include susan's home
        + /home/susan

        # don't backup the other home directories
        - /home/*
    """

The value can either be specified as a list of strings or as a multi-line string 
with one pattern per line.

Patterns are a new experimental feature of *Borg*. They allow you to specify 
what to back up and what not to in a manner that is more flexible than 
:ref:`src_dirs` and :ref:`excludes` allows, and can fully replace them.

For example, notice that /home/susan is included while excluding the directory 
that contains it (/home).

*Emborg* supports the same patterns that `Borg 
<https://borgbackup.readthedocs.io/en/stable/usage/help.html>`_ itself supports. 

When specifying paths in patterns, the paths may be relative or absolute. When 
relative, they are taken to be relative to :ref:`working_dir`.


.. _patterns_from:

patterns_from
~~~~~~~~~~~~~

An alternative to :ref:`patterns`.  You can list your patterns in one or more 
files, one per line, and then specify the file or files using the *exclude_from* 
setting.

.. code-block:: python

    patterns_from = '{config_dir}/patterns'

The value of *patterns_from* may either be a multi-line string, one file per 
line, or a list of strings. The string or strings would be the paths to the file 
or files that contain the patterns. If given as relative paths, they are 
relative to :ref:`working_dir`.  These files are processed directly by *Borg*, 
which does not allow ``~`` to represent users' home directories, unlike the 
patterns specified using :ref:`patterns`.


.. _prefix:

prefix
~~~~~~

Only consider archive names starting with this prefix.

As of Borg 1.2 *prefix* is deprecated and should no longer be used.  Use 
:ref:`glob_archives` instead.  It provides the same basic functionality in a way 
that is a little more general.  For more information, see :ref:`archive`.

Prior to the deprecation of *prefix* it was common in *Emborg* settings file to 
just specify *prefix* and not specify :ref:`archive` with the understanding that 
the default value of *archive* is ``{prefix}-{{now}}``.  So you might have 
something like::

    prefix = '{config_name}-'

in your settings file.  This can be converted to::

    archive = '{config_name}-{{now}}'
    glob_archives = '{config_name}-*'

without changing the intent.


.. _remote_path:

remote_path
~~~~~~~~~~~

Name of *Borg* executable on remote platform.


.. _sparse:

sparse
~~~~~~~~~

Detect sparse holes in input (supported only by fixed chunker).

Requires *Borg* version 1.2 or newer.


.. _threshold:

threshold
~~~~~~~~~

Sets minimum threshold for saved space when compacting a repository with the 
:ref:`compact command <compact>`.  Value is given in percent.

Requires *Borg* version 1.2 or newer.


.. _remote_ratelimit:

remote_ratelimit
~~~~~~~~~~~~~~~~

Set remote network upload rate limit in KiB/s (default: 0=unlimited).

*Borg* has deprecated *remote_ratelimit* in version 1.2.  If you are seeing this 
warning, you should rename *remote_ratelimit* to *upload_ratelimit* in your 
*Emborg* settings file.


.. _umask:

umask
~~~~~

Set umask. This is passed to *Borg*. It uses it when creating files, either 
local or remote. The default is 0o077.


.. _upload_buffer:

upload_buffer
~~~~~~~~~~~~~

Set network upload buffer size in MiB.  By default no buffer is used.  Requires 
*Borg* version 1.2 or newer.


.. _upload_ratelimit:

upload_ratelimit
~~~~~~~~~~~~~~~~

Set upload rate limit in KiB/s when writing to a remote network (default: 
0=unlimited).

Use *upload_ratelimit* when using *Borg* version 1.2 or higher, otherwise use 
*remote_ratelimit*.


.. _working_dir:

working_dir
~~~~~~~~~~~~

All relative paths specified in the configuration files (other than those 
specified to :ref:`include`) are relative to *working_dir*.

*Emborg* changes to the working directory before running the *Borg* *create* 
command, meaning that relative paths specified as roots, excludes, or patterns 
(:ref:`src_dirs`, :ref:`excludes`, :ref:`patterns`, :ref:`exclude_from` or 
:ref:`patterns_from`) are taken to be relative to the working directory.  If you 
use absolute paths for your roots, excludes, and pattern, then the working 
directory must be set to ``/``.

To avoid confusion, it is recommended that all other paths in your configuration 
be specified using absolute paths (ex: :ref:`default_mount_point`,
:ref:`must_exist`, :ref:`patterns_from`, and :ref:`exclude_from`).

If specified, *working_dir* must be specified using an absolute path.
If not specified, *working_dir* defaults to ``/``.
