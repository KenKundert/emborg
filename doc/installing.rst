.. _installing_emborg:

Getting Started
===============

Installing
----------

Many Linux distributions include *Borg* in their package managers. In Fedora it 
is referred to as *borgbackup*. In this case you would install *borg* by running 
the following::

    $ sudo dnf install borgbackup

Alternately, you can download a precompiled version from `Borg Github Releases 
<https://github.com/borgbackup/borg/releases/>`_, which allows you to install 
Borg as an unprivileged user.  You can do so with following commands (they will 
need to be adjusted for to get the latest version)::

    $ cd ~/bin
    $ wget https://github.com/borgbackup/borg/releases/download/1.1.10/borg-linux64
    $ wget https://github.com/borgbackup/borg/releases/download/1.1.10/borg-linux64.asc
    $ gpg --recv-keys "FAF7B393"
    $ gpg --verify borg-linux64.asc
    $ rm borg-linux64.asc
    $ chmod 755 borg-linux64

Download and install *Emborg* as follows (requires Python3.6 or better)::

    $ pip3 install --user emborg

Or, if you want the development version, use::

    $ git clone https://github.com/KenKundert/emborg.git
    $ pip3 install --user ./emborg


Configuring Emborg to Backup A Home Directory
----------------------------------------------

The basic idea behind *Emborg* is that you place all information relavant to 
your backups in two configuration files, which allows you to use *Emborg* to 
perform tasks without re-specifying that information.  Emborg allows you to have 
any number of setups, which you might want if you wanted to backup to multiple 
respositories for redundancy or if you want to use different rules for different 
sets of files. Regardless, you use a separate configuration for each set up, 
plus there is a common configuration file shared by all setups. You are free to 
place most settings in either file, which ever is most convenient.  All the 
configuration files are placed in ~/.config/emborg. If you run *Emborg* without 
creating your configuration files, *Emborg* will create some starter files for 
you.  A configuration is specified using Python, thus the content of these files 
is formatted as Python code and is read by a Python interpreter.

As a demonstration on how to configure *Emborg*, imagine wanting to back up your 
home directory in two ways. First, you want to backup the files to an off-site 
server. Here the expectation is that you would backup once a day on average and 
you would do so interactively so that you can choose an appropriate time.  
Second, you have some free space on your machine that you would like to dedicate 
to recent snapshots of your files. The idea is that you find that you 
occasionally overwrite or delete files that you just spent time creating, and 
you want to run local backups every 10-15 minutes so that you can easily recover 
these files.  To accomplish these two things, you need three configuration 
files.


Shared Settings
^^^^^^^^^^^^^^^

The first file is the shared configuration file:

.. code-block:: python

    configurations = 'backups snapshots'
    default_configuration = 'backups'

This is basically the minimum you can give. Your two configurations are listed 
in *configurations*. It could be a list of strings, but you can also give 
a single string, in which case the string is split on white space. Then you 
specify your default configuration. In this case *backups* will be run 
interactively and *snapshots* will be run on a schedule by *cron*, so the 
default is set to *backups* to make it easier to run interactively.


Configuration for a Remote Repository: *backups*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The second file is the configuration file for *backups*:

.. code-block:: python

    repository = 'backups:archives'
    prefix = '{host_name}-'
    encryption = 'keyfile'
    passphrase = 'crone excess mandate bedpost'

    src_dirs = '~'
    excludes = '''
        ~/.cache
        **/*~
        **/.git
        **/__pycache__
        **/.*.swp
    '''
    exclude_if_present = '.nobackup'

    check_after_create = 'latest'
    prune_after_create = True
    keep_daily = 7
    keep_weekly = 4
    keep_monthly = 12
    keep_yearly = 2

This configuration assumes that you have a *backups* entry in your SSH config 
file that contains the appropriate user name, host name, port number, and such 
for the server that contains your remote repository.  It also assumes that you 
have shared an SSH key with this server so you do not need to specify a password 
each time you back up, and that that key is pre-loaded into your SSH agent.  The 
repository is actually in the *archives* directory on that server, and each 
back-up archive will be prefixed with your local host name, allowing you to 
share this repository with other machines.

You specify what to backup using *src_dirs* and what not to backup using 
*excludes*.  Nominally both *src_dirs* and *excludes* take lists of strings, but 
you can also specify them using a single string, in which case the strings are 
broken into individual lines, any blank lines or lines that begin with ``#`` are 
ignored, and then the white space is removed from the front and back of each 
line.

This configuration file ends with settings that tell *Emborg* to run *check* and 
*prune* operations after creating a backup, and it gives the desired prune 
schedule.

This is just an example, and a rather minimal one at that.  You should not use 
it without understanding each of the settings. The *encryption* setting is 
a particularly important one for you to understand and set properly.  More 
comprehensive information about configuring *Emborg* can be found in the section 
on :ref:`configuring_emborg`.

With this configuration, you can now initialize your repository and use it to 
perform backups.  If the repository does not yet exist, initialize it using::

    $ emborg init

Then perform a back up using::

    $ emborg create

or simply::

    $ emborg

This works because *create* is the default action and *backups* is the default 
configuration.

Then, you can convince yourself it is working as expected by moving a directory 
out of the way and using *Emborg* to restore it::

    $ mv bin bin-saved
    $ emborg restore bin


Configuration for a Local Repository: *snapshots*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The third file is the configuration file for *snapshots*:

.. code-block:: python

    repository = '/mnt/snapshots/{user_name}'
    prefix = '{config_name}-'
    encryption = 'none'

    src_dirs = '~'
    excludes = '''
        ~/.cache
        **/*~
        **/.git
        **/__pycache__
        **/.*.swp
    '''
    prune_after_create = True
    keep_within = '1d'   keep_daily = 7

In this case the repository is on the local machine and it is not encrypted. It 
again backs up your home directory, but for this configuration the archives are 
only kept for a day.

The repository must be initialized before it can be used::

    $ emborg -c snapshots init

Here the desired configuration was specified because it is not the default. Now, 
a *cron* entry can be created using ``crontab -e`` that creates a snapshot every 
10 minutes::

    */10 * * * *  emborg --config snapshots --mute create

Once it has run, you can pull a file from the latest snapshot using::

    $ emborg restore passwords.gpg


Overdue Backups
^^^^^^^^^^^^^^^

*Emborg* allows you to easily determine when your files were last backed up 
using::

    $ emborg due

However, you must remember to run this command. *Emborg* also provides 
*emborg-overdue* to provide automated reminders.  You configure *emborg-overdue* 
using a configuration file: ~/.config/emborg/overdue.conf.  For example:

.. code-block:: python

    default_maintainer = 'me@myhost.com'
    dumper = 'me@myhost.com'
    default_max_age = 36 # hours
    root = '~/.local/share/emborg'
    repositories = [
        dict(host='laptop (snapshots)', path='snapshots.lastbackup', max_age=0.2),
        dict(host='laptop (backups)', path='backups.lastbackup'),
    ]

Then you would configure *cron* to run *emborg-overdue* using something like::

    00 * * * * ~/.local/bin/emborg-overdue --quiet --mail

This runs *emborg-overdue* every hour on the hour, and it reports any delinquent 
backups by sending mail to the appropriate maintainer (the message is sent from 
the *dumper*).  You can specify any number of repositories to check, and for 
each repository you can specify *host* (a descriptive name), *path* (the path to 
the repository from the *root* directory, a *max_age* in hours, and 
a *maintainer*. You can also specify defaults for the *maintainer* and 
*max_age*.  When run, it checks the age of each repository and sends email to 
the appropriate maintainer if it exceeds the maximum allowed age.

In this example the actual repository is not checked directly, rather the 
*lastbackup* file is checked.  This is a file that is updated by *Emborg* after 
every back up. This file is found in the *Emborg* output directory. Every time 
*Emborg* runs it creates a log file that can also be found in this directory.  
That logfile can be viewed directly, or you can view it using the *log* 
command::

    $ emborg log


Configuring Emborg to Backup an Entire Machine
----------------------------------------------

The primary difference between this example and the previous is that *Emborg* 
needs to be configured and run by *root*. This allows all the files on the 
machine to be backed up regardless of who owns them.  Other than being root, the 
mechanics are very much the same.

To start, run emborg to create the initial configuration files::

    # emborg

This creates the ~/.config/emborg directory in the root account and populates it 
with three files: *settings*, *root*, *home*. You can delete *home* and remove 
the reference to it in *settings*, leaving only:

.. code-block:: python

    configurations = 'root'
    default_configuration = 'root'

This assumes that most of the settings will be placed in *root*:

.. code-block:: python

    repository = 'backups:backups/{host_name}'
    prefix = '{config_name}-'
    passphrase = 'western teaser landfall spearhead'
    encryption = 'repokey'

    src_dirs = '/'
    excludes = '''
        /dev
        /home/*/.cache
        /proc
        /root/.cache
        /run
        /tmp
        /var
    '''

    check_after_create = 'latest'
    prune_after_create = True
    keep_daily = 7
    keep_weekly = 4
    keep_monthly = 12

Again, this is a rather minimal example. In this case, *repokey* is used as the 
encryption method, which is only suitable if the repository is on a server you 
control.

As before you need to initialize the repository before it can be used::

    # emborg init

To assure that the backups are run daily, the following is added to 
/etc/cron.daily/emborg::

    #/bin/sh
    # Run root backups

    emborg --mute --config root create

This is preferred for laptops because cron.daily is guaranteed to run each day 
as long as machine is turned on for any reasonable length of time.
