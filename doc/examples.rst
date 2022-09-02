.. _emborg examples:

Examples
========

When first run, *Emborg* creates the settings directory and populates it with 
two configurations that you can use as starting points. Those two configurations 
make up our first two examples.


.. _root example:

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

Here is the contents of the settings file: /root/.config/emborg/settings:

.. code-block:: python

    configurations = 'root'
    default_configuration = 'root'

    # basic settings
    notify = "root@continuum.com"
    upload_ratelimit = 2000     # bandwidth limit in kbps
    prune_after_create = True
    check_after_create = 'latest'

    # repository settings
    repository = 'backups:/mnt/backups/{host_name}-{user_name}-{config_name}'
    archive = '{prefix}{{now:%Y%m%d}}'
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

And here is the contents of the *root* configuration file: /root/.config/emborg/root:

.. code-block:: python

    # Settings for root configuration
    passphrase = 'carvery overhang vignette platitude pantheon sissy toddler truckle'
    encryption = 'repokey'
    one_file_system = False

    src_dirs = '/'
    excludes = '''
        /dev
        /home/*/.cache
        /mnt
        /proc
        /run
        /sys
        /tmp
        /var/cache
        /var/lock
        /var/run
        /var/tmp
    '''                         # list of files or directories to skip

This file contains the passphrase, and so you should be careful to set its 
permissions so that nobody but root can see its contents. Also, this 
configuration uses *repokey* as the encryption method, which is suitable when 
you control the server that holds the repository and you know it to be secure.  

Once this configuration is complete and has been tested, you would want to add 
a crontab entry so that it runs on a routine schedule. On servers that are 
always running, you could use `crontab -e` and add an entry like this:

.. code-block:: text

    30 03 * * * emborg --mute --config root create

For individual workstations or laptops that are likely to be turned off at 
night, one would instead create an executable script in /etc/cron.daily that 
contains the following:

.. code-block:: bash

    #/bin/sh
    # Run root backups

    emborg --mute --config root create

Assume that this file is named *emborg*. Then after creating it, you would make 
it executable with:

.. code-block:: bash

    $ chmod a+x /etc/cron.daily/emborg

Scripts in /etc/cron.daily are one once a day, either at a fixed time generally 
early in the morning or, if not powered up at that time, shortly after being 
powered up.


.. _user examples:

User
----

The *home* configuration is a suitable starting point for someone that just 
wants to backup their home directory on their laptop.  In this example, two 
configurations are created, one to be run manually that copies all files to 
a remote repository, and a second that runs every few minutes and creates 
snapshots of key working directories.  This second allows you to quickly recover 
from mistakes you make during the day without having to go back to yesterday's 
copy of a file as a starting point.

Here is the contents of the shared settings file: ~/.config/emborg/settings.

.. code-block:: python

    # configurations
    configurations = 'home snapshots'
    default_configuration = 'home'

    # basic settings
    notifier = 'notify-send -u normal {prog_name} "{msg}"'

    # repository settings
    compression = 'lz4'

    # shared filter settings
    exclude_if_present = '.nobackup'
    exclude_caches = True


.. _home example:

Home
^^^^

Here is the contents of the *home* configuration file: ~/.config/emborg/home.
This configuration backs up to a remote untrusted repository and is expected to 
be run interactively, perhaps once per day.

.. code-block:: python

    repository = 'backups:/mnt/borg-backups/repositories/{host_name}-{user_name}-{config_name}'
    prefix = '{config_name}-'
    encryption = 'keyfile'
    avendesora_account = 'laptop-borg'
    needs_ssh_agent = True
    upload_ratelimit = 2000
    prune_after_create = True
    check_after_create = 'latest'

    src_dirs = '~'                      # paths to be backed up
    excludes = '''
        ~/.cache
        **/.hg
        **/.git
        **/__pycache__
        **/*.pyc
        **/.*.swp
        **/.*.swo
        **/*~
    '''

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
*backups* should be configured to use a private key and that key should be 
preloaded into your SSH agent.

This passphrase for this configuration is kept in `Avendesora 
<https://avendesora.readthedocs.io>`_, and the encryption method is *keyfile*.  
As such, it is critical that you extract the keyfile from *Borg* and copy it and 
your *Avendesora* files to a safe place so that both the keyfile and passphrase 
are available if you lose your disk. You can use `SpareKeys 
<https://github.com/kalekundert/sparekeys>`_ to do this for you. Otherwise 
extract the keyfile using:

.. code-block:: bash

    $ emborg borg key export @repo key.borg

*cron* is not used for this configuration because the machine, being a laptop, 
is not guaranteed to be on at any particular time of the day. So instead, you 
would simply run *Emborg* on your own at a convenient time using:

.. code-block:: bash

    $ emborg

You can use the *Emborg due* command to remind you if a backup is overdue. You 
can wire it into status bar programs, such as *i3status* to give you a visual 
reminder, or you can configure cron to check every hour and notify you if they 
are overdue. This one triggers a notification:

.. code-block:: text

    0 * * * * emborg --mute due --days 1 || notify-send 'Backups are overdue'

And this one sends an email:

.. code-block:: text

    0 * * * * emborg --mute due --days 1 --mail me@mydomain.com

Alternately, you can use :ref:`emborg-overdue <client_overdue>`.


.. _snapshot example:

Snap Shots
^^^^^^^^^^

And finally, here is the contents of the *snapshots* configuration file: 
~/.config/emborg/snapshots.

.. code-block:: python

    repository = '~/.cache/snapshots'
    encryption = 'none'

    src_dirs = '~'
    excludes = '''
        ~/.cache
        ~/media
        **/.hg
        **/.git
        **/__pycache__
        **/*.pyc
        **/.*.swp
        **/.*.swo
        **/.~
    '''

    # prune settings
    keep_hourly = 12
    prune_after_create = True
    check_after_create = False

To run this configuration every 10 minutes, add the following entry to your 
crontab file using 'crontab -e':

.. code-block:: text

    0,10,20,30,40,50 * * * * emborg --mute --config snapshots create


.. _rsync.net example:

Rsync.net
---------

*Rsync.net* is a commercial option for off-site storage. In fact, they give you 
a discount if you use `Borg Backup <https://www.rsync.net/products/attic.html>`_.

Once you sign up for *Rsync.net* you can access your storage using *sftp*, 
*scp*, *rsync* or *borg* of course.  *ssh* access is also available, but only 
for a limited set of commands.

You would configure *Emborg* for *Rsync.net* in much the same way you would for 
any remote server.  Of course, you should use some form of *keyfile* based 
encryption to keep your files secure.  The only thing to be aware of is that by 
default they provide a old version of borg. To use a newer version, set the 
``remote_path`` to ``borg1``.

.. code-block:: python

    repository = '78548@ch-s012.rsync.net:repo'
    encryption = 'keyfile'
    remote_path = 'borg1'

    ...

In this example, ``78548`` is the user name and ``ch-s012.rsync.net`` is the 
server they assign to you.  ``repo`` is the name of the directory that is to 
contain your *Borg* repository. You are free to name it whatever you like and 
you can have as many as you like, with the understanding that you are 
constrained in the total amount of storage you consume.


.. _borgbase example:

BorgBase
--------

`BorgBase <https://www.borgbase.com>`_ is another commercial alternative for 
*Borg Backups*.  It allows full *Borg* access, append-only *Borg* access, and 
*rsync* access, though each form of access requires its own unique SSH key.

Again, you should use some form of *keyfile* encryption to keep your files 
secure, and *BorgBase* recommends *Blake2* encryption as being the fastest 
alternative.

.. code-block:: python

    repository = 'zMNZCv4B@zMNZCv4B.repo.borgbase.com:repo'
    encryption = 'keyfile-blake2'

    ...

In this example, ``zMNZCv4B`` is the user name and 
``zMNZCv4B.repo.borgbase.com`` is the server they assign to you.  You may 
request any number of repositories, with each repository getting its own 
username and hostname. ``repo`` is the name of the directory that is to contain 
your *Borg* repository and cannot be changed.
