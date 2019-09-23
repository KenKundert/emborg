.. _installing:

Getting Started
===============

Many Linux distributes include *Borg* in their package managers. In Fedora it is 
referred to as *borgbackup*. In this case you would install *borg* by running 
the following::

    sudo dnf install borgbackup

Alternately, you can download a precompiled version from `Borg Github Releases 
<https://github.com/borgbackup/borg/releases/>`_. You can do so with following 
commands (they will need to be adjusted for to get the latest version)::

    cd ~/bin
    wget https://github.com/borgbackup/borg/releases/download/1.1.10/borg-linux64
    wget https://github.com/borgbackup/borg/releases/download/1.1.10/borg-linux64.asc
    gpg --recv-keys "FAF7B393"
    gpg --verify borg-linux64.asc
    rm borg-linux64.asc
    chmod 755 borg-linux64

Download and install *Emborg* as follows (requires Python3.6 or better)::

    pip3 install --user emborg

Or, if you want the development version, use::

    git clone https://github.com/KenKundert/emborg.git
    pip3 install --user ./emborg

Then you will need to create your *Emborg* settings directory (~/.config/emborg) 
and create a shared settings file 'settings' and then one or more files, one for 
each configuration you want.  If you run 'emborg' without creating the settings 
directory, it will create it for you and populate it with starter files you must 
edit to use.  Specifically it creates a shared settings file, and then a *home* 
and *root* configuration. You generally only need one. Start from *home* if you 
are backing up your home directory, and start from *root* if you are backing up 
the root file system.  Delete the one you do not need.

Normally people have just two files, the shared settings file and one 
configuration file, perhaps named 'home' because it used to back up your home 
directory. However, you may wish to have a second configuration dedicated to 
creating snapshots of your files every 15 minutes or so. These snapshots may be 
kept locally and only for a day or so while your primary backups are kept 
remotely and kept long term.

Settings may be placed in either the shared settings file or the configuration 
specific file. The ones placed in the configuration specific file dominate.
The shared settings file must contain at least one setting, *configurations*, 
which is a list of the available configurations.

You can find descriptions of all available settings with::

    emborg settings -a

There are certain settings that are worth highlighting.

**repository**

The destination for the backups. A typical value might be::

    repository = 'archives:/mnt/backups/{host_name}-{user_name}-{config_name}'

where in this example 'archives' is the hostname and /mnt/backups is the 
absolute path to the directory that is to contain your Borg repositories, 
and {host_name}-{user_name}-{config_name} is the directory to contain this 
repository.  For a local repository you would use something like this::

    repository = '/mnt/backups/{host_name}-{user_name}-{config_name}'

These examples assume that */mnt/backups* contains many independent 
repositories.  Borg allows you to make a single repository the target of 
multiple backup configurations, and in this way you can further benefit from its 
ability to de-duplicate files.  In this case you might want to use a less 
granular name for you repository.

**archive** and **prefix**

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
Specifically the *check*, *delete*, *info*, *list*, *mount*, and *prune* 
commands all use *prefix*.

When sharing a repository between multiple backup configurations, it is 
important that all prefixes be unique. Be careful of one prefix that is a prefix 
of another. For example, prefixes of *root* and *root2* would be bad because 
*root* is a prefix of *root2*.  In the examples given, *prefix* ends with '-' to 
reduce this risk.

If you do not specify either *archive* or *prefix*, then you get the following 
defaults::

    archive = '{config_name}-{{now}}'
    prefix = '{config_name}-'

If you specify only *prefix*, then *archive* becomes::

    archive = '<prefix>{{now}}'

If you specify only *archive*, then *prefix* remains unset. This is only 
suitable when there is only one backup configuration using a repository.

If you want *prefix* and want to customize *now*, you should give both *prefix* 
and *archive*. For example, you can reduce the length of the timestamp using::

    archive = '{host_name}-{{now:%Y%m%d}}'
    prefix = '{host_name}-'

In this example the host name was used as the prefix rather than the 
configuration name. When specifying both the *prefix* and the *archive*, the 
leading part of *archive* should match *prefix*.  Be aware that by including 
only the date in the archive name rather than the full timestamp, you are 
limiting yourself to creating one archive per day.


**encryption**

The encryption mode that is used when first creating the repository. Common 
values are *none*, *authenticated*, *repokey*, and *keyfile*.  The repository is 
encrypted if you choose *repokey* or *keyfile*. In either case the passphrase 
you provide does not encrypt repository. Rather the repository is encrypted 
using a key that is randomly generated by *Borg*.  You passphrase encrypts the 
key.  Thus, to restore your files you will need both the key and the passphrase. 
With *repokey* your key is copied to the repository, so it can be used with 
trusted repositories. Use *keyfile* if the remote repository is not trusted. It 
does not copy the key to the repository, meaning that it is extremely important 
for you export the key using 'borg key export' and keep a copy in a safe place 
along with the passphrase.


**passphrase**

The passphrase used when encrypting the encryption key.  This is used as an 
alternative to *avendesora_account*.  Be sure to make the file that contains it 
unreadable by others.


**passcommand**

An alternate to *passphrase*. *Borg* runs this command to get your passphrase.


**avendesora_account**

Another alternative to *passphrase*. The name of the *Avendesora* account used 
to hold the passphrase for the encryption key. Using *Avendesora* keeps your 
passphrase out of your settings file, but requires that GPG agent be available 
and loaded with your private key.  This is normal when running interactively.  
When running batch, say from *cron*, you can use the Linux *keychain* command to 
retain your GPG credentials for you.


**src_dirs**

The list of directories to be backed up.  A typical value might be::

    src_dirs = '~'.split()


**excludes**

A list of files to exclude from the backups.  Typical value might be::

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


Once you have set up your configuration directory, you will need to create your 
repository. To do so, assure that the parent directory of your repository exists 
and is writable on the remote server.  Then run::

    emborg init

Once you have done that you can create your first backup using::

    emborg create
