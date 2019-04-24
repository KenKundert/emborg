.. _configuring:

Configuring
===========

Settings file go in ~/.config/emborg. You need a shared settings file and then 
one file for each repository you need.  Except for *configurations* and 
*default_configuration* any setting may be place in the shared file or the 
repository specific file.  If a setting shows in both files, the version on the 
configuration specific file dominates.


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


Configuration Settings
----------------------

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
