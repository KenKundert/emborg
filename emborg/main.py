# Usage {{{1
"""
Emborg Backups

Backs up the contents of a file hierarchy.  A front end for Borg's
encrypted incremental backup utility.

Usage:
    emborg [options] [<command> [<args>...]]

Options:
    -c <cfgname>, --config <cfgname>  Specifies the configuration to use.
    -d, --dry-run                     Run Borg in dry run mode.
    -h, --help                        Output basic usage information.
    -m, --mute                        Suppress all output.
    -n, --narrate                     Send emborg and Borg narration to stdout.
    -q, --quiet                       Suppress optional output.
    -r, --relocated                   Acknowledge that repository was relocated.
    -v, --verbose                     Make Borg more verbose.
    --no-log                          Do not create log file.
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
import sys
from docopt import docopt
from inform import (
    Error, Inform, LoggingCache, cull, display, error, os_error, terminate
)
from . import __released__, __version__
from .command import Command
from .hooks import Hooks
from .emborg import ConfigQueue, Emborg

# Globals {{{1
version = f"{__version__} ({__released__})"
commands = """
Commands:
{commands}

Use 'emborg help <command>' for information on a specific command.
Use 'emborg help' for list of available help topics.
"""
synopsis = __doc__
expanded_synopsis = synopsis + commands.format(commands=Command.summarize())


# Main {{{1
def main():
    with Inform(
        error_status = 2,
        flush = True,
        logfile = LoggingCache(),
        prog_name = 'emborg',
        version = version,
    ) as inform:

        try:
            worst_exit_status = 0

            # emborg fails if the current working directory does not exist and
            # the message returned by OSError does not make the problem obvious.
            try:
                os.getcwd()
            except OSError as e:
                raise Error(os_error(e), codicil="Does the current working directory exist?")

            # read command line
            cmdline = docopt(expanded_synopsis, options_first=True, version=version)
            config = cmdline["--config"]
            command = cmdline["<command>"]
            args = cmdline["<args>"]
            if cmdline["--mute"]:
                inform.mute = True
            if cmdline["--quiet"]:
                inform.quiet = True
            if cmdline["--relocated"]:
                os.environ['BORG_RELOCATED_REPO_ACCESS_IS_OK'] = 'YES'
            emborg_opts = cull(
                [
                    "verbose" if cmdline["--verbose"] else None,
                    "narrate" if cmdline["--narrate"] else None,
                    "dry-run" if cmdline["--dry-run"] else None,
                    "no-log" if cmdline["--no-log"] else None,
                ]
            )
            if cmdline["--narrate"]:
                inform.narrate = True

            Hooks.provision_hooks()

            # find the command
            cmd, cmd_name = Command.find(command)

            # execute the command initialization
            exit_status = cmd.execute_early(cmd_name, args, None, emborg_opts)
            if exit_status is not None:
                terminate(exit_status)

            queue = ConfigQueue(cmd)
            while queue:
                with Emborg(config, emborg_opts, queue=queue, cmd_name=cmd_name) as settings:
                    try:
                        exit_status = cmd.execute(
                            cmd_name, args, settings, emborg_opts
                        )
                    except Error as e:
                        exit_status = 2
                        settings.fail(e, cmd=' '.join(sys.argv))
                        e.terminate()

                if exit_status and exit_status > worst_exit_status:
                    worst_exit_status = exit_status

            # execute the command termination
            exit_status = cmd.execute_late(cmd_name, args, None, emborg_opts)
            if exit_status and exit_status > worst_exit_status:
                worst_exit_status = exit_status

        except Error as e:
            exit_status = 2
            e.report()
        except OSError as e:
            exit_status = 2
            error(os_error(e))
        except KeyboardInterrupt:
            exit_status = 0
            display("Terminated by user.")
        if exit_status and exit_status > worst_exit_status:
            worst_exit_status = exit_status
        terminate(worst_exit_status)
