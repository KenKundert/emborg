.. _examples:

Examples
========

When first run, *Emborg* creates the settings directory and populates it with 
two configurations that you can use as starting points. Those two configurations 
make up our first two examples.


Root
----

The *root* configuration is a suitable starting point for someone that wants to 
backup an entire machine, including both system and user files. In order to have 
permission to access the files, one must run this configuration as the *root* 
user.

This configuration was constructed assuming that the backups would be run 
automatically at a fixed time using cron.  Since this user only has one 
configuration, it is largely arbitrary which file each setting resides in, 
however both files must exist, and the *settings* file must contain 
*configurations* and *default_configuration*.

Here is the contents of the settings file: /root/.config/emborg/settings::

    configurations = 'root'
    default_configuration = 'root'

    # basic settings
    notify = "root@continuum.com"
    remote_ratelimit = 2000     # bandwidth limit in kbps
    prune_after_create = True
    check_after_create = True

    # repository settings
    repository = 'backups:/mnt/backups/{host_name}-{user_name}-{config_name}'
    archive = '{config_name}-{{now:%Y%m%d}}'
    prefix = '{config_name}-'
    compression = 'lz4'

    # shared filter settings
    exclude_if_present = '.nobackup'
    exclude_caches = True

    # prune settings
    keep_within = '1d'          # keep all archives created within this interval
    keep_hourly = 48            # number of hourly archives to keep
    keep_daily = 14             # number of daily archives to keep
    keep_weekly = 8             # number of weekly archives to keep
    keep_monthly = 24           # number of monthly archives to keep
    keep_yearly = 24            # number of yearly archives to keep

In this case we are assuming that *backups* (used in *repository*) is an entry 
in your SSH config file that points to the server that stores your repository.  
To be able to run this configuration autonomously from cron, *backups* must be 
configured to use a private key that does not have a passphrase.

And here is the contents of the *root* configuration file: /root/.config/emborg/root::

    # Settings for root configuration
    passphrase = 'carvery overhang vignette platitude pantheon sissy toddler truckle'
    encryption = 'repokey'
    one_file_system = False

    src_dirs = '/'.split()      # absolute paths to directories to be backed up
    excludes = '''
        /dev
        /mnt
        /proc
        /run
        /sys
        /tmp
        /var/cache
        /var/lock
        /var/log
        /var/run
        /var/spool
        /var/tmp
    '''.split()                 # list of files or directories to skip

This file contains the passphrase, and so you should be careful to set its 
permissions so that nobody but root can see its contents. Also, this 
configuration uses *repokey* as the encryption method, which is suitable when 
you control the server that holds the repository and you know it to be secure.  

Once this configuration is complete and has been tested, you would want to add 
a crontab entry so that it runs on a routine schedule. To do so, you would run 
`crontab -e` and add an entry like this::

    30 03 * * * emborg --mute --config root create


User
----

The *home* configuration is a suitable starting point for someone that just 
wants to backup their home directory on their laptop.  In this example, two 
configurations are created, one to be run manually that copies all files to 
a remote repository, and a second that runs every few minutes and backs up key 
working directories as a cache.  This second allows you to quickly recover from 
mistakes you make during the day without having to go back to yesterday's copy 
of a file as a starting point.

Here is the contents of the settings file: /root/.config/emborg/settings::

    # configurations
    configurations = 'home cache'
    default_configuration = 'home'

    # basic settings
    notifier = 'notify-send -u normal {prog_name} "{msg}"'

    # repository settings
    compression = 'lz4'

    # shared filter settings
    exclude_if_present = '.nobackup'
    exclude_caches = True


Home
^^^^

Here is the contents of the *home* configuration file: ~/.config/emborg/home::

    repository = 'backups:/mnt/borg-backups/repositories/{host_name}-{user_name}-{config_name}'
    encryption = 'keyfile'
    avendesora_account = 'laptop-borg'
    needs_ssh_agent = True
    remote_ratelimit = 2000
    prune_after_create = True
    check_after_create = True

    src_dirs = '~'.split()              # paths to be backed up
    excludes = '''
        ~/.cache
        ~/tmp
        ~/**/.hg
        ~/**/.git
        ~/**/__pycache__
        ~/**/*.pyc
        ~/**/.*.swp
        ~/**/.*.swo
        ~/**/.~
    '''.split()

    exclude_if_present = '.nobackup'
    run_before_backup = '(cd ~/src; ./clean)'

    # prune settings
    keep_within = '1d'                        # keep all archives created within this interval
    keep_hourly = 48                          # number of hourly archives to keep
    keep_daily = 14                           # number of daily archives to keep
    keep_weekly = 8                           # number of weekly archives to keep
    keep_monthly = 24                         # number of monthly archives to keep
    keep_yearly = 24                          # number of yearly archives to keep

In this case we are assuming that *backups* (used in *repository*) is an entry 
in your SSH config file that points to the server that stores your repository.  
Since you are running this configuration interactively, *backups* should be 
configured to use a private key and that key should be preloaded into your SSH 
agent.

This configuration keeps the passphrase is kept in `Avendesora 
<https://avendesora.readthedocs.io>`_, and the encryption method is *keyfile*.  
As such, it is critical that you extract the keyfile from *Borg* and copy it and 
your *Avendesora* files to a safe place so that both the keyfile and passphrase 
are available if you lose your disk. You can use `SpareKeys 
<https://github.com/kalekundert/sparekeys>`_ to do this for you. Otherwise 
extract the keyfile using::

    emborg borg key export @repo key.borg

*cron* is not used for this configuration because the machine, being a laptop, 
is not guaranteed to be on at any particular time of the day. So instead, you 
would simply run *Emborg* on your own at a convenient time using::

    emborg

You can use the *Emborg due* command to remind you if a backup is overdue. You 
can wire it into status bar programs, such as *i3status* to give you a visual 
reminder, or you can configure cron to check every hour and notify you if they 
are overdue::

    0 * * * * emborg --mute due --days 1 || notify-send 'Backups are overdue'


Cache
^^^^^

And finally, here is the contents of the *cache* configuration file: 
~/.config/emborg/cache::

    repository = '/home/ken/.cache/backups/{user_name}'
    encryption = 'none'

    src_dirs = '~'.split()   # absolute paths to directories to be backed up
    excludes = '''
        ~/.cache
        ~/media
        ~/tmp
        ~/**/.hg
        ~/**/.git
        ~/**/__pycache__
        ~/**/*.pyc
        ~/**/.*.swp
        ~/**/.*.swo
        ~/**/.~
    '''.split()
    exclude_if_present = '.nobackup'

    # prune settings
    keep_within = '1d'
    keep_hourly = 24
    prune_after_create = True
    check_after_create = False

To run this configuration every 15 minutes, add the following entry to your 
crontab file using 'crontab -e'::

    0,15,30,45 * * * * emborg --config cache create
