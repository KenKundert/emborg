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
    -m, --mail           Send mail message if backup is overdue
    -n, --notify         Send notification if backup is overdue
    -p, --no-passes      Do not show hosts that are not overdue
    -q, --quiet          Suppress output to stdout
    -v, --verbose        Give more information about each repository
    -M, --message <msg>  Status message template for each repository
    --version            Show software version

The program requires a configuration file: ~/.config/emborg/overdue.conf. The
contents are described here:
    https://emborg.readthedocs.io/en/stable/utilities.html#overdue

The message given by --message may contain the following keys in braces:
    host: replaced by the host field from the config file, a string.
    max_age: replaced by the max_age field from the config file, a float in hours.
    mtime: replaced by modification time, a datetime object.
    hours: replaced by the number of hours since last update, a float.
    age: replaced by time since last update, a string.
    overdue: is the back-up overdue.

The status message is a Python formatted string, and so the various fields can include
formatting directives.  For example:
- strings than include field width and justification, ex. {host:>20}
- floats can include width, precision and form, ex. {hours:0.1f}
- datetime can include Arrow formats, ex: {mdime:DD MMM YY @ H:mm A}
- overdue can include true/false strings: {overdue:PAST DUE!/current}
"""

# License {{{1
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
import pwd
import socket
from textwrap import dedent
import arrow
from docopt import docopt
from inform import (
    Color,
    Error,
    Inform,
    InformantFactory,
    conjoin,
    display,
    error,
    fatal,
    fmt,
    get_prog_name,
    is_str,
    os_error,
    terminate,
    truth,
    warn,
)

from . import __released__, __version__
from .preferences import CONFIG_DIR, DATA_DIR, OVERDUE_FILE, OVERDUE_LOG_FILE
from .python import PythonFile
from .shlib import Run, to_path, set_prefs as set_shlib_prefs
from .utilities import read_latest

# Globals {{{1
set_shlib_prefs(use_inform=True, log_cmd=True)
username = pwd.getpwuid(os.getuid()).pw_name
hostname = socket.gethostname()
now = arrow.now()

default_colorscheme = "dark"
current_color = "green"
overdue_color = "red"

verbose_status_message = dedent("""\
    HOST: {host}
        sentinel file: {path!s}
        last modified: {mtime}
        since last change: {hours:0.1f} hours
        maximum age: {max_age} hours
        overdue: {overdue}
""")
terse_status_message = "{host}: {age} ago"
mail_status_message = dedent(
    f"""
    Backup of {{host}} is overdue:
       from: {username}@{hostname} at {now}
       message: the backup sentinel file has not changed in {{hours:0.1f}} hours.
       sentinel file: {{path!s}}
    """
).strip()

error_message = dedent(
    f"""
    {get_prog_name()} generated the following error:
        from: {username}@{hostname} at {now}
        message: {{}}
    """
)


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
    cmdline = docopt(__doc__, version=version)
    quiet = cmdline["--quiet"]
    problem = False
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
        flush=True, quiet=quiet, logfile=log,
        colorscheme=colorscheme, version=version
    ):
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
            max_age = float(max_age) if max_age else default_max_age
            try:
                path = to_path(root, path)
                if path.is_dir():
                    paths = list(path.glob("index.*"))
                    if not paths:
                        raise Error("no sentinel file found.", culprit=path)
                    if len(paths) > 1:
                        raise Error("too many sentinel files.", *paths, sep="\n    ")
                    path = paths[0]
                mtime = arrow.get(path.stat().st_mtime)
                if path.suffix == '.nt':
                    latest = read_latest(path)
                    mtime = latest.get('create last run')
                    if not mtime:
                        raise Error('backup time is not available.', culprit=path)
                delta = now - mtime
                hours = 24 * delta.days + delta.seconds / 3600
                age = mtime.humanize(only_distance=True)
                overdue = truth(hours > max_age)
                report = report_as_overdue if overdue else report_as_current
                if overdue or not cmdline["--no-passes"]:
                    replacements = dict(
                        host=host, path=path, mtime=mtime, age=age,
                        hours=hours, max_age=max_age, overdue=overdue
                    )
                    try:
                        report(status_message.format(**replacements))
                    except KeyError as e:
                        fatal(
                            f"‘{e.args[0]}’ is an unknown key.",
                            culprit='--message',
                            codicil=f"Choose from: {conjoin(replacements.keys())}.",
                        )

                if overdue:
                    problem = True
                    subject = f"backup of {host} is overdue"
                    msg = fmt(mail_status_message)
                    send_mail(maintainer, subject, msg)
            except OSError as e:
                problem = True
                msg = os_error(e)
                error(msg)
                if maintainer:
                    send_mail(
                        maintainer,
                        f"{get_prog_name()} error",
                        error_message.format(msg),
                    )
            except Error as e:
                problem = True
                e.report()
                if maintainer:
                    send_mail(
                        maintainer,
                        f"{get_prog_name()} error",
                        error_message.format(str(e)),
                    )
        terminate(problem)
