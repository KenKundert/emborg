.. _configuring:

Configuring
===========

Settings file go in ~/.config/emborg. You need a shared settings file and then 
one file for each repository you need.  Except for *configurations* and 
*default_configuration* any setting may be place in the shared file or the 
repository specific file.  If a setting shows in both files, the version on the 
configuration specific file dominates.

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
    check_after_create = True             # run check as the last step of an archive creation
    notify = "me@mydomain.com"            # email address to notify when things go wrong
    notifier = 'notify-send -u normal {prog_name} "{msg}"'
                                          # program used to send realtime notifications
                                          # generally you use notify or notifier, but not both
                                          # use notifier for interactive backups 
                                          # and notify for scheduled backups
                                          # notification program
    remote_ratelimit = 2000               # bandwidth limit in kbps
    umask = '077'                         # umask to use when creating the archives
    keep_within = '1d'                    # keep all archives within this time interval
    keep_hourly = '48'                    # number of hourly archives to keep
    keep_daily = '7'                      # number of daily archives to keep
    keep_weekly = '4'                     # number of weekly archives to keep
    keep_monthly = '12'                   # number of weekly archives to keep
    keep_yearly = '2'                     # number of weekly archives to keep

If you encrypt your backups, you can specify the encryption key in this file as 
*passphrase*. In this case, you should be careful to assure the file is not 
readable by others (chmod 600 settings).  Alternatively, you can use `Avendesora 
<https://avendesora.readthedocs.io>`_ to securely hold your key by specifying 
the Avendesora account name of the key to *avendesora_account*.


Configurations
--------------

Each backup configuration must have a settings file in ~/.config/emborg. The 
name of the file is the name of the backup configuration.  It might look like 
the following::

    repository = 'archives:/mnt/backups/{host_name}/{config_name}'
                                          # remote directory for repository
    archive = '{host_name}-{{now}}'       # naming pattern used for the archives
        # May contain {<name>} where <name> may be any of host_name, user_name, 
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
or Emborg's program name ('prog_name'). An example of this is shown in both
*repository* and *archive* above.  Doubling up the braces acts to escape them.  
In this way you gain access to *Borg* settings. *archive* shows and example of 
that.

It is generally better to specify *prefix* rather than *archive*, though you can 
specify both if you wish.  If *archive* is not specified and *prefix* is, then 
*archive* is created by adding '{{now}}' to *prefix*. If *archive* is specified 
but *prefix* is not, then *archive* is used as given and *prefix* is not passed 
to the *prune* command. In this case you should not have multiple configurations 
backup into the same repository.

For example, if *prefix* is '{config_name}-' and *archive* is not given then 
*archive* becomes '{config_name}-{{now}}'.  If neither *archive* or *prefix* is 
specified, then '{config_name}-{{now}}' is used for *archive* and 
'{config_name}-' is used for *prefix*.  One would specify both *archive* and 
*prefix* when you wanted to use a different format for *now*. For example::

    archive = '{config_name}-{{now:%Y%m%d}}'
    prefix = '{config_name}-'


Includes
--------

Any setting may include the contents of another file by using an *include*. You 
may either specify a single include file as a string or a collection as a list 
of strings::

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

    configurations = 'root home lamp all=root,home,lamp'

In this case *root*, *home* and *lamp* are simple configurations and *all* is 
a composite configuration.  *root*, *home*, and *lamp* would have configuration 
files whereas *all* would not.

You can run a specific configuration with:

    emborg -c root extract ~/bin

You can run all three configurations with:

    emborg -c all create

Only certain commands support composite configurations. Specifically, *create*, 
*check*, *configs*, *due*, *help*, *info*, *prune*, and *version* support 
composite configures.  Specifying a composite configuration to a command that 
does not support them results in an error.
