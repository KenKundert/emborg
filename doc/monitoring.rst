.. _utilities:
.. _monitoring:

Monitoring
==========


Log Files
---------

When there are problems, the log file can help you understand what is going 
wrong.  *Emborg* writes a log file to the *Emborg* data directory.  On Linux 
systems that would be `~/.local/share/emborg`.  Other systems use more awkward 
locations, so *Emborg* allows you to specify the data directory using the 
`XDG_DATA_HOME` environment variable.  If `XDG_DATA_HOME` is set to 
`/home/$HOME/.local/share`, then the *Emborg* log files will be written to 
`/home/$HOME/.local/share/emborg`, as on Linux systems.

Besides visiting the *Emborg* data directory and viewing the log file directly,
you can use the :ref:`log command <log>` to view the log file.

*Emborg* overwrites its log file every time it runs.  You can use :ref:`ntlog 
<ntlog accessory>` to gather log files as they are created into a composite log 
file.


Due and Info
------------

The :ref:`due <due>` and :ref:`info <info>` commands allow you to interactively 
check on the current status of your backups.  Besides the :ref:`create <create>` 
command, it is good hygiene to run the :ref:`prune <prune>`, :ref:`compact 
<compact>` and :ref:`check <check>` on a regular basis.  Either the :ref:`due 
<due>` or :ref:`info <info>` command can be used to determine when each were 
last run.


.. _emborg_overdue:

Overdue
-------

.. _server_overdue:

Checking for Overdue Backups from the Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Emborg* contains an additional executable, *emborg-overdue*, that can be run on 
the destination server to determine whether the backups have been performed 
recently.  It reads its own settings file in `overdue.conf`, contained in the 
:ref:`Emborg configuration directory <configuring_emborg>`,  that is also 
a Python file and may contain the following settings:

.. code-block:: text

    default_maintainer (email address -- mail is sent to this person upon failure)
    default_max_age (hours)
    dumper (email address -- mail is sent from this person)
    root (default directory for repositories)
    repositories (string or array of dictionaries)

Here is an example config file:

.. code-block:: python

    default_maintainer = 'root@continuum.com'
    dumper = 'dumper@continuum.com'
    default_max_age = 12  # hours
    root = '/mnt/borg-backups/repositories'
    colorscheme = 'dark'
    status_message = "{host}: {age} ago{overdue: — PAST DUE}"
    repositories = [
        dict(host='mercury (/)', path='mercury-root-root'),
        dict(host='venus (/)', path='venus-root-root'),
        dict(host='earth (/)', path='earth-root-root'),
        dict(host='mars (/)', path='mars-root-root'),
        dict(host='jupiter (/)', path='jupiter-root-root'),
        dict(host='saturn (/)', path='saturn-root-root'),
        dict(host='uranus (/)', path='uranus-root-root'),
        dict(host='neptune (/)', path='neptune-root-root'),
        dict(host='pluto (/)', path='pluto-root-root'),
    ]

The dictionaries in *repositories* can contain the following fields: *host*, 
*path*, *maintainer*, *max_age*.

*host*:
    An arbitrary string that is used as description of the repository.  It is 
    included in the email that is sent when problems occur to identify the 
    backup and so should be unique.  It is a good idea for it to contain both 
    the host name and the source directory being backed up.
*path*:
    Is either the archive name or a full absolute path to the archive.  The 
    modification time of the target of this path is used as the time of the last 
    backup.  If *path* is an absolute path, it is used, otherwise it is added to 
    the end of *root*.

    If the path contains a colon (‘:’), then everything before the colon is 
    taken to be an SSH hostname and everything after the colon is assumed to be 
    the name of the *emborg-overdue* command on that local machine without 
    arguments.  In most cases the colon will be the last character of the path, 
    in which case the command name is assumed to be ‘emborg-overdue’.  This 
    command is run on the remote host and the results reported locally.  The 
    version of *emborg* on the remote host must be 1.41 or greater.
*maintainer*:
    An email address, an email is sent to this address if there is an issue.  
    *max_age* is the number of hours that may pass before an archive is 
    considered overdue.
*max_age*:
    The maximum age in hours.  If the back-up occurred more than this many hours 
    in the past it is considered over due.

*repositories* can also be specified as multi-line string:

.. code-block:: python

    repositories = """
        # HOST      | NAME or PATH      | MAINTAINER           | MAXIMUM AGE (hours)
        mercury (/) | mercury-root-root |                      |
        venus (/)   | venus-root-root   |                      |
        earth (/)   | earth-root-root   |                      |
        mars (/)    | mars-root-root    |                      |
        jupiter (/) | jupiter-root-root |                      |
        saturn (/)  | saturn-root-root  |                      |
        uranus (/)  | uranus-root-root  |                      |
        neptune (/) | neptune-root-root |                      |
        pluto (/)   | pluto-root-root   |                      |
    """

If *repositories* is a string, it is first split on newlines, anything beyond 
a # is considered a comment and is ignored, and the finally the lines are split 
on '|' and the 4 values are expected to be given in order.  If the *maintainer* 
is not given, the *default_maintainer* is used. If *max_age* is not given, the 
*default_max_age* is used.

There are some additional settings available:

*default_maintainer*:
    Email address of the account running the checks.  This will be the sender 
    address on any email sent as a result of an over due back-up.
*dumper*:
    Email address of the account monitoring the checks.  This will be the 
    recipient address on any email sent as a result of an over due back-up.
*root*:
    The directory used as the root when converting relative paths given in 
    *repositories* to absolute paths.  By default this will be the *Emborg* log 
    file directory.
*default_max_age*:
    The default maximum age in hours.  It is used if a maximum age is not given 
    for a particular repository.
*colorscheme*:
    The color scheme of your terminal.  May be "dark" or "light" or None.  If 
    None, the output is not colored.
*message*:
    The format of the summary for each host.  The string may contain keys within 
    braces that will be replaced before output.  The following keys are 
    supported:

    | *host*: replaced by the host field from the config file, a string.
    | *max_age*: replaced by the max_age field from the config file, a float.
    | *mtime*: replaced by modification time, a datetime object.
    | *hours*: replaced by the number of hours since last update, a float.
    | *age*: replaced by time since last update, a string.
    | *overdue*: is the back-up overdue, a boolean.
    | *locked*: is the back-up currently active, a boolean.

    The message is a Python formatted string, and so the various fields can include
    formatting directives.  For example:

    - strings than include field width and justification, ex. {host:>20}
    - floats can include width, precision and form, ex. {hours:0.1f}
    - datetimes can include Arrow formats, ex: {mtime:DD MMM YY @ H:mm A}
    - booleans can include true/false strings: ex. {overdue:PAST DUE!/current}

To run the program interactively, just make sure *emborg-overdue* has been 
installed and is on your path. Then type:

.. code-block:: bash

    $ emborg-overdue

It is also common to run *emborg-overdue* on a fixed schedule from cron. To do 
so, run:

.. code-block:: bash

    $ crontab -e

and add something like the following:

.. code-block:: text

    34 5 * * * ~/.local/bin/emborg-overdue --quiet --mail

or:

.. code-block:: text

    34 5 * * * ~/.local/bin/emborg-overdue --quiet --notify

to your crontab.

The first example runs emborg-overdue at 5:34 AM every day.  The use of the 
``--mail`` option causes *emborg-overdue* to send mail to the maintainer when 
backups are found to be overdue.

.. note::

    By default Linux machines are not configured to send email.  If you are 
    using the ``--mail`` option to *emborg-overdue* be sure that to check that 
    it is working.  You can do so by sending mail to your self using the *mail* 
    or *mailx* command.  If you do not receive your test message you will need 
    to set up email forwarding on your machine.  You can do so by installing and 
    configuring `PostFix as a null client
    <http://www.postfix.org/STANDARD_CONFIGURATION_README.html#null_client>`_.

The second example uses ``--notify``, which sends a notification if a back-up is 
overdue and there is not access to the tty (your terminal).

Alternately you can run *emborg-overdue* from cron.daily (described in the 
:ref:`root example <root example>`).


.. _client_overdue:

Checking for Overdue Backups from the Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*emborg-overdue* can also be configured to run on the client.  This can be used 
when you do not control the server and so cannot run *emborg-overdue* there.  
The configuration is identical, except you give the path to the *latest.nt* 
file.  For example:

.. code-block:: python

    default_maintainer = 'me@continuum.com'
    dumper = 'me@continuum.com'
    default_max_age = 12  # hours
    root = '~/.local/share/emborg'
    repositories = [
        dict(host='earth (cache)', path='cache.latest.nt', max_age=0.2),
        dict(host='earth (home)', path='home.latest.nt'),
        dict(host='sol', path='sol:'),
    ]

Notice the last entry, the one for *sol*.  Its path contains a colon, so it is 
a remote check.  The others are local checks.  The remote check splits *path* at 
the colon.  In this case, the split gives 'sol' and ''.  The first component is 
taken to be a host name and the second is the name of the emborg-overdue command 
on that host.  In this case the second component is empty so *emborg-overdue* is 
used.  On the remote checks, the *emborg-overdue* command is run remotely on the 
specified host and the results are included in the output.  This generally 
requires that you have the SSH keys for the remote host in your SSH agent, which 
is generally not the case when *emborg-overdue* is being run from cron.  In this 
case you should use the ``--local`` option to suppress remote queries.


.. _monitoring_services:

Monitoring Services
-------------------

Various monitoring services are available on the web.  You can configure 
*Emborg* to notify them when back-up jobs have started and finished.  These 
services allow you to monitor many of your routine tasks and assure they have 
completed recently and successfully.

There are many such services available and they are not difficult to add.  If 
the service you prefer is not currently available, feel free to request it on 
`Github <https://github.com/KenKundert/emborg/issues>`_ or add it yourself and 
issue a pull request.

.. _cronhub:

CronHub.io
~~~~~~~~~~

When you sign up with `cronhub.io <https://cronhub.io>`_ and configure the 
health check for your *Emborg* configuration, you will be given a UUID (a 32 
digit hexadecimal number partitioned into 5 parts by dashes).  Add that to the 
following setting in your configuration file:

.. code-block:: python

    cronhub_uuid = '51cb35d8-2975-110b-67a7-11b65d432027'

If given, this setting should be specified on an individual configuration.  It 
causes a report to be sent to *CronHub* each time an archive is created.  
A successful report is given if *Borg* returns with an exit status of 0 or 1, 
which implies that the command completed as expected, though there might have 
been issues with individual files or directories.  If *Borg* returns with an 
exit status of 2 or greater, a failure is reported.


.. _healthchecks:

HealthChecks.io
~~~~~~~~~~~~~~~

When you sign up with `healthchecks.io <https://healthchecks.io>`_ and configure 
the health check for your *Emborg* configuration, you will be given a UUID (a 32 
digit hexadecimal number partitioned into 5 parts by dashes).  Add that to the 
following setting in your configuration file:

.. code-block:: python

    healthchecks_uuid = '51cb35d8-2975-110b-67a7-11b65d432027'

If given, this setting should be specified on an individual configuration.  It 
causes a report to be sent to *HealthChecks* each time an archive is created.  
A successful report is given if *Borg* returns with an exit status of 0 or 1, 
which implies that the command completed as expected, though there might have 
been issues with individual files or directories.  If *Borg* returns with an 
exit status of 2 or greater, a failure is reported.
