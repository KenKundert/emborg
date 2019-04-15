# Usage {{{1
"""
Emborg Backups

Backs up the contents of a file hierarchy.  A front end for Borg's
encrypted incremental backup utility.

Usage:
    emborg [options] [<command> [<args>...]]

Options:
    -c <cfgname>, --config <cfgname>  Specifies the configuration to use.
    -h, --help                        Output basic usage information.
    -m, --mute                        Suppress all output.
    -n, --narrate                     Send emborg and Borg narration to stdout.
    -t, --trial-run                   Run Borg in dry run mode.
    -v, --verbose                     Make Borg more verbose.
    --no-log                          Do not create log file.
"""

commands = """
Commands:
{commands}

Use 'emborg help <command>' for information on a specific command.
Use 'emborg help' for list of available help topics.
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
# along with this program.  If not, see http://www.gnu.org/licenses/.


# Imports {{{1
from . import __version__, __released__
from .command import Command
from .settings import Settings
from inform import Inform, Error, cull, fatal, display, terminate, os_error
from docopt import docopt

# Globals {{{1
synopsis = __doc__
expanded_synopsis = synopsis + commands.format(commands=Command.summarize())
version = f'{__version__} ({__released__})'

from .command import Command
# Main {{{1
def main():
    with Inform(error_status=2, flush=True, version=version) as inform:
        # read command line
        cmdline = docopt(expanded_synopsis, options_first=True, version=version)
        config = cmdline['--config']
        command = cmdline['<command>']
        args = cmdline['<args>']
        if cmdline['--mute']:
            inform.mute = True
        options = cull([
            'verbose' if cmdline['--verbose'] else '',
            'narrate' if cmdline['--narrate'] else '',
            'trial-run' if cmdline['--trial-run'] else '',
            'no-log' if cmdline['--no-log'] else '',
        ])
        if cmdline['--narrate']:
            inform.narrate = True

        try:
            cmd, cmd_name = Command.find(command)

            with Settings(config, cmd.REQUIRES_EXCLUSIVITY, options) as settings:
                try:
                    exit_status = cmd.execute(cmd_name, args, settings, options)
                except Error as e:
                    settings.fail(e)
                    e.terminate(True)

        except KeyboardInterrupt:
            display('Terminated by user.')
            exit_status = 0
        except Error as e:
            e.terminate()
        except OSError as e:
            fatal(os_error(e))
        terminate(exit_status)
