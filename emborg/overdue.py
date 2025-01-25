# Usage {{{1
"""
Overdue Emborg Backups

This program notifies you if backups have not been run recently.  It can be run
either from the server (the destination) or from the client (the source). It
simply lists those archives that are out-of-date.  If you specify --mail, email
is sent that describes the situation if a backup is overdue.

Usage:
    emborg-overdue [options]

Options:
    -c, --no-color       Do not color the output
    -h, --help           Output basic usage information
    -l, --local          Only report on local repositories
    -m, --mail           Send mail message if backup is overdue
    -n, --notify         Send notification if backup is overdue
    -N, --nt             Output summary in NestedText format
    -p, --no-passes      Do not show hosts that are not overdue
    -q, --quiet          Suppress output to stdout
    -v, --verbose        Give more information about each repository
    -M, --message <msg>  Status message template for each repository
    --version            Show software version

The program requires a configuration file, overdue.conf, which should be placed
in the Emborg configuration directory, typically ~/.config/emborg.  The contents
are described here:

    https://emborg.readthedocs.io/en/stable/monitoring.html#overdue

The message given by --message may contain the following keys in braces:
    host: replaced by the host field from the config file, a string.
    max_age: replaced by the max_age field from the config file, a float in hours.
    mtime: replaced by modification time, a datetime object.
    hours: replaced by the number of hours since last update, a float.
    age: replaced by time since last update, a string.
    overdue: is the back-up overdue, a boolean.
    locked: is the back-up currently active, a boolean.

The status message is a Python formatted string, and so the various fields can include
formatting directives.  For example:
- strings than include field width and justification, ex. {host:>20}
- floats can include width, precision and form, ex. {hours:0.1f}
- datetimes can include Arrow formats, ex: {mtime:DD MMM YY @ H:mm A}
- boolean can include true/false strings, ex: {overdue:PAST DUE!/current}
"""

# License {{{1
# Copyright (C) 2018-2024 Kenneth S. Kundert
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.


# Imports {{{1
import os
import sys
import pwd
import socket
import arrow
from docopt import docopt, DocoptExit
from inform import (
    Color,
    Error,
    Inform,
    InformantFactory,
    conjoin,
    dedent,
    display,
    error,
    fatal,
    get_prog_name,
    is_str,
    os_error,
    output,
    terminate,
    truth,
    warn,
)
import nestedtext as nt

from . import __released__, __version__
from .preferences import CONFIG_DIR, DATA_DIR, OVERDUE_FILE, OVERDUE_LOG_FILE
from .python import PythonFile
from .shlib import Run, to_path, set_prefs as set_shlib_prefs
from .utilities import read_latest, when

# Globals {{{1
set_shlib_prefs(use_inform=True, log_cmd=True)
username = pwd.getpwuid(os.getuid()).pw_name
hostname = socket.gethostname()
now = arrow.now()

# colors {{{2
default_colorscheme = "dark"
current_color = "green"
overdue_color = "red"

# message templates {{{2
verbose_status_message = dedent("""\
    HOST: {host}
        sentinel file: {path!s}
        last modified: {mtime}
        since last change: {hours:0.1f} hours
        maximum age: {max_age} hours
        overdue: {overdue}
        locked: {locked}
""", strip_nl='l')

terse_status_message = "{host}: {age} ago{locked: (currently active)}{overdue: — PAST DUE}"

mail_status_message = dedent("""
    Backup of {host} is overdue:
       the backup sentinel file has not changed in {hours:0.1f} hours.
""", strip_nl='b')

error_message = dedent(f"""
    {get_prog_name()} generated the following error:
        from: {username}@{hostname} at {now}
        message: {{}}
""", strip_nl='b')

# Utilities {{{1
# get_local_data {{{2
def get_local_data(path, host, max_age):
    if path.is_dir():
        paths = list(path.glob("index.*"))
        if not paths:
            raise Error("no sentinel file found.", culprit=path)
        if len(paths) > 1:
            raise Error("too many sentinel files.", *paths, sep="\n    ")
        path = paths[0]
        locked = list(path.glob('lock.*'))
    mtime = arrow.get(path.stat().st_mtime)
    if path.suffix == '.nt':
        latest = read_latest(path)
        locked = (path.parent / path.name.replace('.latest.nt', '.lock')).exists()
        mtime = latest.get('create last run')
        if not mtime:
            raise Error('backup time is not available.', culprit=path)
    delta = now - mtime
    hours = 24 * delta.days + delta.seconds / 3600
    overdue = truth(hours > max_age)
    locked = truth(locked)
    yield dict(
        host=host, path=path, mtime=mtime, hours=hours, max_age=max_age,
        overdue=overdue, locked=locked
    )

# get_remote_data {{{2
def get_remote_data(name, path):
    host, _, cmd = path.partition(':')
    cmd = cmd or "emborg-overdue"
    display(f"\n{name}:")
    try:
        ssh = Run(['ssh', host, cmd, '--nt'], 'sOEW2')
        for repo_data in nt.loads(ssh.stdout, top=list):
            if 'mtime' in repo_data:
                repo_data['mtime'] = arrow.get(repo_data['mtime'])
            if 'overdue' in repo_data:
                repo_data['overdue'] = truth(repo_data['overdue'] == 'yes')
            if 'hours' in repo_data:
                repo_data['hours'] = float(repo_data.get('hours', 0))
            if 'max_age' in repo_data:
                repo_data['max_age'] = float(repo_data.get('max_age', 0))
            if 'locked' in repo_data:
                repo_data['locked'] = truth(repo_data['locked'] == 'yes')
            else:
                repo_data['locked'] = truth(False)
            yield repo_data
    except Error as e:
        e.report(culprit=host)

    if ssh.status > 1:
        raise Error(
            "error found by remote overdue process.",
                culprit=host, codicil=ssh.stderr.strip()
        )

# fixed() {{{2
# formats float using fixed point notation while removing trailing zeros
def fixed(num, prec=2):
    return format(num, f".{prec}f").strip('0').strip('.')

# Main {{{1
def main():
    # read the settings file
    try:
        settings_file = PythonFile(CONFIG_DIR, OVERDUE_FILE)
        settings = settings_file.run()
    except Error as e:
        e.terminate()

    # gather needed settings
    default_maintainer = settings.get("default_maintainer")
    default_max_age = settings.get("default_max_age", 28)
    dumper = settings.get("dumper", f"{username}@{hostname}")
    repositories = settings.get("repositories")
    root = settings.get("root")
    colorscheme = settings.get("colorscheme", default_colorscheme)
    status_message = settings.get("status_message", terse_status_message)

    version = f"{__version__} ({__released__})"
    try:
        cmdline = docopt(__doc__, version=version)
    except DocoptExit as e:
        sys.stderr.write(str(e) + '\n')
        terminate(3)
    quiet = cmdline["--quiet"]
    exit_status = 0
    report_as_current = InformantFactory(
        clone=display, message_color=current_color
    )
    report_as_overdue = InformantFactory(
        clone=display, message_color=overdue_color,
        notify=cmdline['--notify'] and not Color.isTTY()
    )
    if cmdline["--message"]:
        status_message = cmdline["--message"]
    if cmdline["--no-color"]:
        colorscheme = None
    if cmdline["--verbose"]:
        status_message = verbose_status_message

    # prepare to create logfile
    log = to_path(DATA_DIR, OVERDUE_LOG_FILE) if OVERDUE_LOG_FILE else False
    if log:
        data_dir = to_path(DATA_DIR)
        if not data_dir.exists():
            try:
                # data dir does not exist, create it
                data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            except OSError as e:
                warn(os_error(e))
                log = False

    with Inform(
        flush=True, quiet=quiet or cmdline["--nt"], logfile=log,
        error_status=2, colorscheme=colorscheme, version=version,
        stream_policy = 'header' if cmdline['--nt'] else 'termination'
    ):
        overdue_hosts = {}

        # process repositories table
        backups = []
        if is_str(repositories):
            for line in repositories.split("\n"):
                line = line.split("#")[0].strip()  # discard comments
                if not line:
                    continue
                backups.append([c.strip() for c in line.split("|")])
        else:
            for each in repositories:
                backups.append(
                    [
                        each.get("host"),
                        each.get("path"),
                        each.get("maintainer"),
                        each.get("max_age"),
                    ]
                )

        def send_mail(recipient, subject, message):
            if cmdline["--mail"]:
                if cmdline['--verbose']:
                    display(f"Reporting to {recipient}.\n")
                mail_cmd = ["mailx", "-r", dumper, "-s", subject, recipient]
                Run(mail_cmd, stdin=message, modes="soeW0")

        # check age of repositories
        for host, path, maintainer, max_age in backups:
            maintainer = default_maintainer if not maintainer else maintainer
            max_age = float(max_age if max_age else default_max_age)
            try:
                if ':' in str(path):
                    if cmdline['--local']:
                        repos_data = []
                    else:
                        repos_data = get_remote_data(host, str(path))
                else:
                    repos_data = get_local_data(to_path(root, path), host, max_age)
                for repo_data in repos_data:
                    repo_data['age'] = when(repo_data['mtime'])
                    overdue = repo_data['overdue']
                    report = report_as_overdue if overdue else report_as_current

                    if overdue or not cmdline["--no-passes"]:
                        if cmdline["--nt"]:
                            output(nt.dumps([repo_data], converters={float:fixed}, default=str))
                        else:
                            try:
                                report(status_message.format(**repo_data))
                            except ValueError as e:
                                fatal(e, culprit=(host, '--message'))
                            except KeyError as e:
                                fatal(
                                    f"‘{e.args[0]}’ is an unknown key.",
                                    culprit=(host, '--message'),
                                    codicil=f"Choose from: {conjoin(repo_data.keys())}.",
                                )

                    if overdue:
                        exit_status = max(exit_status, 1)
                        overdue_hosts[host] = mail_status_message.format(**repo_data)

            except OSError as e:
                exit_status = max(exit_status, 2)
                msg = os_error(e)
                error(msg)
                if maintainer:
                    send_mail(
                        maintainer,
                        f"{get_prog_name()} error",
                        error_message.format(msg),
                    )
            except Error as e:
                exit_status = max(exit_status, 2)
                e.report()
                if maintainer:
                    send_mail(
                        maintainer,
                        f"{get_prog_name()} error",
                        error_message.format(str(e)),
                    )

        if overdue_hosts:
            if len(overdue_hosts) > 1:
                subject = "backups are overdue"
            else:
                subject = "backup is overdue"
            messages = '\n\n'.join(overdue_hosts.values())
            send_mail(maintainer, subject, messages)

        terminate(exit_status)
