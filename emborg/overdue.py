# Usage {{{1
"""
Overdue Emborg Backups

This program, run on the repository server, notifies you if backups have not
been run recently.  It either does it by simply listing those archives that are
out-of-date, or if you specify --mail, email is sent that describes the
situation if a backup is overdue.

Usage:
    emborg-overdue [options]

Options:
    -c, --no-color   Do not color the output
    -h, --help       Output basic usage information
    -m, --mail       Send mail message if backup is overdue
    -p, --no-passes  Do not show hosts that are not overdue
    -q, --quiet      Suppress output to stdout
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
    display,
    error,
    get_prog_name,
    is_str,
    os_error,
    terminate,
    warn,
)
from shlib import Run, set_prefs, to_path

from . import __released__, __version__
from .preferences import CONFIG_DIR, DATA_DIR, OVERDUE_FILE, OVERDUE_LOG_FILE
from .python import PythonFile

# Globals {{{1
set_prefs(use_inform=True)
username = pwd.getpwuid(os.getuid()).pw_name
hostname = socket.gethostname()
now = arrow.now()

overdue_message = dedent(
    f"""
    Backup of {{host}} is overdue:
       from: {username}@{hostname} at {now}
       message: the backup sentinel file has not changed in {{age:0.0f}} hours.
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
    version = f"{__version__} ({__released__})"
    cmdline = docopt(__doc__, version=version)
    quiet = cmdline["--quiet"]
    problem = False
    use_color = Color.isTTY() and not cmdline["--no-color"]
    passes = Color("green", enable=use_color)
    fails = Color("red", enable=use_color)

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

    with Inform(flush=True, quiet=quiet, logfile=log, version=version):

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
                delta = now - mtime
                age = 24 * delta.days + delta.seconds / 3600
                report = age > max_age
                color = fails if report else passes
                if report or not cmdline["--no-passes"]:
                    display(
                        color(
                            dedent(
                                f"""
                                HOST: {host}
                                    sentinel file: {path!s}
                                    last modified: {mtime}
                                    since last change: {age:0.1f} hours
                                    maximum age: {max_age} hours
                                    overdue: {report}
                                """
                            ).lstrip()
                        )
                    )

                if report:
                    problem = True
                    subject = f"backup of {host} is overdue"
                    msg = overdue_message.format(host=host, path=path, age=age)
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
