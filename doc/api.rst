.. _emborg_api:

Python API
==========

*Emborg* has a simple API that allows you to run borg commands. Here is an 
example taken from `sparekeys <https://github.com/kalekundert/sparekeys>`_ that 
exports the keys from your *Borg* repository so then can be backed up 
separately::

    from emborg import Emborg

    with Emborg('home') as emborg:
        borg = emborg.run_borg(
            cmd = 'key export',
            args = [emborg.destination(), archive / '.config/borg.repokey']
        )
        if borg.stdout:
            print(borg.stdout.rstrip())

*Emborg* takes the config name as an argument, if not given the default config 
is used. It provides the following useful methods and attributes:


**repository**

The path to the repository.


**destination(archive)**

Returns the full path to the archive. If Archive is False or None, then the path 
to the repository it returned. If Archive is True, then the default archive name 
as taken from settings file is used. This is only appropriate when creating new 
repositories.


**run_borg(cmd, args, borg_opts, emborg_opts)**

Runs a *Borg* command.

*cmd* is the desired *Borg* command (ex: 'create', 'prune', etc.).

*args* contains the command line arguments (such as the repository or 
archive). It may also contain any additional command line options not 
automatically provided.  It may be a list or a string. If it is a string, it 
is split at white space.

*borg_opts* are the command line options needed by *Borg*. If not given, it 
is created for you by *Emborg* based upon your configuration settings.

Finally, *emborg_opts* is a list that may contain any of the following options: 
'verbose', 'narrate', 'dry-run', or 'no-log'.

This function runs the *Borg* command and returns a process object that 
allows you access to stdout via the *stdout* attribute.


**run_borg_raw(args)**

Runs a raw *Borg* command without interpretation except for replacing 
a ``@repo`` argument with the path to the repository.

*args* contains all command line options and arguments except the path to 
the executable.


**borg_options(cmd, emborg_opts)**

This function returns the default *Borg* command line options, those that would 
be used in *run_borg* if *borg_opts* is not set. It can be used when 
constructing a custom *borg_opts*.


**value(name, default='')**

Returns the value of a setting from an *Emborg* configuration. If not set, 
*default* is returned.


You can examine the emborg/command.py file for inspiration and examples on how 
to use the *Emborg* API.
