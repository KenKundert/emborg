# Commands

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
from .collection import Collection
from .preferences import (
    BORG_SETTINGS,
    DEFAULT_COMMAND,
    EMBORG_SETTINGS,
    PROGRAM_NAME,
)
from .utilities import two_columns, render_paths, gethostname
hostname = gethostname()
from inform import (
    Color, Error,
    codicil, conjoin, full_stop, is_str, narrate, os_error, output,
    render, warn,
)
from docopt import docopt
from shlib import mkdir, rm, to_path, Run, set_prefs
set_prefs(use_inform=True, log_cmd=True)
from textwrap import dedent
import arrow
import json
import sys


# Utilities {{{1
# title() {{{2
def title(text):
    return full_stop(text.capitalize())

# get_available_archives() {{{2
def get_available_archives(settings):
    # run borg
    borg = settings.run_borg(
        cmd = 'list',
        args = ['--json', settings.destination()],
    )
    try:
        data = json.loads(borg.stdout)
        return data['archives']
    except json.decoder.JSONDecodeError as e:
        raise Error('Could not decode output of Borg list command.', codicil=e)

def get_nearest_archive(settings, date):
    archives = get_available_archives(settings)
    try:
        date = arrow.get(date)
    except arrow.parser.ParserError:
        raise Error('invalid date specification.', culprit=date)
    for archive in archives:
        if arrow.get(archive['time']) >= date:
            return archive['archive']
    return None

# get_available_files() {{{2
def get_available_files(settings, archive):
    # run borg
    borg = settings.run_borg(
        cmd = 'list',
        args = ['--json-lines', settings.destination(archive)],
    )
    try:
        files = []
        for line in borg.stdout.splitlines():
            files.append(json.loads(line))
        return files
    except json.decoder.JSONDecodeError as e:
        raise Error('Could not decode output of Borg list command.', codicil=e)

# Command base class {{{1
class Command(object):
    @classmethod
    def commands(cls):
        for cmd in cls.__subclasses__():
            if hasattr(cmd, 'NAMES'):
                yield cmd
            for sub in cmd.commands():
                if hasattr(sub, 'NAMES'):
                    yield sub

    @classmethod
    def commands_sorted(cls):
        for cmd in sorted(cls.commands(), key=lambda c: c.get_name()):
            yield cmd

    @classmethod
    def find(cls, name):
        if not name:
            name = DEFAULT_COMMAND
        for command in cls.commands():
            if name in command.NAMES:
                return command, command.NAMES[0]
        raise Error('unknown command.', culprit=name)

    @classmethod
    def execute(cls, name, args, settings, options):
        narrate('running {} command'.format(name))
        return cls.run(name, args if args else [], settings, options)

    @classmethod
    def summarize(cls, width=16):
        summaries = []
        for cmd in Command.commands_sorted():
            summaries.append(two_columns(', '.join(cmd.NAMES), cmd.DESCRIPTION))
        return '\n'.join(summaries)

    @classmethod
    def get_name(cls):
        return cls.NAMES[0]

    @classmethod
    def help(cls):
        text = dedent("""
            {title}

            {usage}
        """).strip()
        return text.format(
            title=title(cls.DESCRIPTION), usage=cls.USAGE,
        )


# Borg command {{{1
class Borg(Command):
    NAMES = 'borg'.split()
    DESCRIPTION = 'run a raw borg command.'
    USAGE = dedent("""
        Usage:
            emborg borg <borg_args>...

        An argument that is precisely '@repo' is replaced with the path to the
        repository.  The passphrase is set before the command is run.
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args, options_first=True)
        borg_args = cmdline['<borg_args>']

        # run borg
        settings.run_borg_raw(borg_args)


# BreakLock command {{{1
class BreakLock(Command):
    NAMES = 'breaklock break-lock'.split()
    DESCRIPTION = 'breaks the repository and cache locks.'
    USAGE = dedent("""
        Usage:
            emborg breaklock
            emborg break-lock

        Breaks both the local and the repository locks. Be sure Borg is no longer
        running before using this command.
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        # run borg
        borg = settings.run_borg(
            cmd = 'break-lock',
            args = [settings.destination()],
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())
        rm(settings.lockfile)


# Create command {{{1
class Create(Command):
    NAMES = 'create backup'.split()
    DESCRIPTION = 'create an archive of the current files'
    USAGE = dedent("""
        Usage:
            emborg create [options]
            emborg backup [options]

        Options:
            -f, --fast    skip pruning and checking for a faster backup on a slow network

        To see the files listed as they are backed up, use the Emborg -v option.
        This can help you debug slow create operations.
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)

        # check for required settings
        src_dirs = render_paths(settings.src_dirs)
        if not src_dirs:
            raise Error('src_dirs: setting has no value.')

        # check the dependencies are available
        for each in settings.values('must_exist'):
            path = to_path(each)
            if not path.exists():
                raise Error(
                    'does not exist, perform setup and restart.',
                    culprit=each
                )

        # run prerequisites
        cmds = settings.value('run_before_backup')
        if is_str(cmds):
            cmds = [cmds]
        for cmd in cmds:
            narrate('running pre-backup script:', cmd)
            try:
                Run(cmd, 'SoEW')
            except Error as e:
                e.reraise(culprit=('run_before_backup', cmd.split()[0]))

        # run borg
        try:
            settings.run_borg(
                cmd = 'create',
                args = [settings.destination(True)] + render_paths(settings.src_dirs),
                emborg_opts = options,
            )
        except Error as e:
            if e.stderr and 'is not a valid repository' in e.stderr:
                e.reraise(
                    codicil = "Run 'emborg init' to initialize the repository."
                )
            else:
                raise

        # update the date files
        narrate('update date file')
        now = arrow.now()
        settings.date_file.write_text(str(now))

        # run any scripts specified to be run after a backup
        cmds = settings.value('run_after_backup')
        if is_str(cmds):
            cmds = [cmds]
        for cmd in cmds:
            narrate('running post-backup script:', cmd)
            try:
                Run(cmd, 'SoEW')
            except Error as e:
                e.reraise(culprit=('run_after_backup', cmd.split()[0]))

        if cmdline['--fast']:
            return

        # prune the archives if requested
        try:
            # check the archives if requested
            activity = 'checking'
            if settings.check_after_create:
                narrate('checking archive')
                check = Check()
                check.run('check', [], settings, options)

            activity = 'pruning'
            if settings.prune_after_create:
                narrate('pruning archives')
                prune = Prune()
                prune.run('prune', [], settings, options)
        except Error as e:
            e.reraise(codicil=(
                f'This error occurred while {activity} the archives.',
                'No error was reported while creating the archive.'
            ))


# Check command {{{1
class Check(Command):
    NAMES = 'check'.split()
    DESCRIPTION = 'checks the repository and its archives'
    USAGE = dedent("""
        Usage:
            emborg check [options]

        Options:
            -v, --verify-data    perform a full integrity verification (slow)
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        verify = ['--verify-data'] if cmdline['--verify-data'] else []

        # run borg
        borg = settings.run_borg(
            cmd = 'check',
            args = verify + [settings.destination()],
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# Configs command {{{1
class Configs(Command):
    NAMES = 'configs'.split()
    DESCRIPTION = 'list available backup configurations'
    USAGE = dedent("""
        Usage:
            emborg configs
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        configurations = Collection(settings.configurations)
        if configurations:
            output('Available Configurations:', *configurations, sep='\n    ')
        else:
            output('No configurations available.')


# Delete command {{{1
class Delete(Command):
    NAMES = 'delete'.split()
    DESCRIPTION = 'delete an archive currently contained in the repository'
    USAGE = dedent("""
        Usage:
            emborg delete <archive>
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        archive = cmdline['<archive>']

        # run borg
        borg = settings.run_borg(
            cmd = 'delete',
            args = [settings.destination(archive)],
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# Diff command {{{1
class Diff(Command):
    NAMES = 'diff'.split()
    DESCRIPTION = 'show the differences between two archives'
    USAGE = dedent("""
        Usage:
            emborg diff <archive1> <archive2>
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        archive1 = cmdline['<archive1>']
        archive2 = cmdline['<archive2>']

        # run borg
        borg = settings.run_borg(
            cmd = 'diff',
            args = [settings.destination(archive1), archive2],
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# Due command {{{1
class Due(Command):
    NAMES = 'due'.split()
    DESCRIPTION = 'days since last backup'
    USAGE = dedent("""
        Used with status bar programs, such as i3status, to make user aware that
        backups are due.

        Usage:
            emborg due [options]

        Options:
            -d <num>, --days <num>     emit message if this many days have passed
                                       since last backup
            -m <msg>, --message <msg>  the message to emit
            -e <addr>, --email <addr>  send email message rather than print message

        If you specify the days, then the message is only printed if the backup
        is overdue.  If not overdue, nothing is printed. The message is always
        printed if days is not specified.

        If you specify the message, the following replacements are available:
            days: the number of days since the backup
            elapsed: the time that has elapsed since the backup

        Examples:
            > emborg due
            The latest complete archive was create 19 hours ago.

            > emborg due -d0.5 -m "It has been {days:.1f} days since the last backup."
            It has been 0.8 days since the last backup.

            > emborg due -d90 -m "It has been {elapsed} since the last backup."
            It has been 4 months since the last backup.
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        email = cmdline['--email']

        def gen_message(date):
            if cmdline['--message']:
                since_last_backup = arrow.now() - date
                days = since_last_backup.total_seconds()/86400
                elapsed = date.humanize(only_distance=True)
                return cmdline['--message'].format(
                    days=days, elapsed=elapsed
                )
            else:
                return f'The latest complete archive was created {date.humanize()}.'

        if email:
            def report(msg):
                Run(
                    ['mail', '-s', f'{PROGRAM_NAME}: backup is overdue', email],
                    stdin=dedent(f'''
                        {msg}
                        config = {settings.config_name}
                        source host = {hostname}
                        source directories = {', '.join(str(d) for d in settings.src_dirs)}
                        destination = {settings.repository}
                    ''').lstrip(),
                    modes='soeW'
                )
        else:
            def report(msg):
                output(msg)

        # Get date of last backup and warn user if it is overdue
        date_file = settings.date_file
        try:
            backup_date = arrow.get(date_file.read_text())
        except FileNotFoundError:
            backup_date = arrow.get('19560105', 'YYYYMMDD')
        except arrow.parser.ParserError:
            raise Error('date not given in iso format.', culprit=date_file)
        if cmdline.get('--days'):
            since_last_backup = arrow.now() - backup_date
            days = since_last_backup.total_seconds()/86400
            try:
                if days > float(cmdline['--days']):
                    report(gen_message(backup_date))
                    if not email:
                        return 1
            except ValueError:
                raise Error('expected a number for --days.')
            return

        # Otherwise, simply report age of backups
        report(gen_message(backup_date))


# Extract command {{{1
class Extract(Command):
    NAMES = 'extract'.split()
    DESCRIPTION = 'recover file or files from archive'
    USAGE = dedent("""
        Usage:
            emborg [options] extract <path>...

        Options:
            -d <date>, --date <date>            date of the desired version of paths
            -a <archive>, --archive <archive>   name of the archive to use

        You extract a file or directory using:

            emborg extract home/ken/src/verif/av/manpages/settings.py

        Use manifest to determine what path you should specify to identify the
        desired file or directory (they will paths relative to /).
        Thus, the paths should look like absolute paths with the leading slash
        removed.  The paths may point to directories, in which case the entire
        directory is extracted. It may also be a glob pattern.

        If you do not specify an archive or date, the most recent archive is
        used.  You can extract the version of a file or directory that existed
        on a particular date using:

            emborg extract --date 2015-04-01 home/ken/src/verif/av/manpages/settings.py

        Or, you can extract the version from a particular archive using:

            emborg extract --archive kundert-2018-12-05T12:54:26 home/ken/src/verif/av/manpages/settings.py

        The extracted files will be placed in the current working directory with
        there original hierarchy. Thus, the above commands create the file:

            ./home/ken/src/verif/av/manpages/settings.py
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        paths = cmdline['<path>']
        archive = cmdline['--archive']
        date = cmdline['--date']

        # remove initial / from paths
        src_dirs = [str(p).lstrip('/') for p in settings.src_dirs]
        new_paths = [p.lstrip('/') for p in paths]
        if paths != new_paths:
            for path in paths:
                if path.startswith('/'):
                    warn('removing initial /.', culprit=path)
            paths = new_paths

        # assure that paths correspond to src_dirs
        unknown_path = False
        for path in paths:
            if not any([path.startswith(src_dir) for src_dir in src_dirs]):
                unknown_path = True
                warn('unknown path.', culprit=path)
        if unknown_path:
            codicil('Paths should start with:', conjoin(src_dirs))

        # get the desired archive
        if date and not archive:
            archive = get_nearest_archive(settings, date)
            if not archive:
                raise Error('archive not available.', culprit=date)
        if not archive:
            archives = get_available_archives(settings)
            if not archives:
                raise Error('no archives are available.')
            archive = archives[-1]['name']
        output('Archive:', archive)

        # run borg
        borg = settings.run_borg(
            cmd = 'extract',
            args = [settings.destination(archive)] + paths,
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# Help {{{1
class Help(Command):
    NAMES = 'help'.split()
    DESCRIPTION = 'give information about commands or other topics'
    USAGE = dedent("""
        Usage:
            emborg help [<topic>]
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)

        from .help import HelpMessage
        HelpMessage.show(cmdline['<topic>'])


# Info command {{{1
class Info(Command):
    NAMES = 'info'.split()
    DESCRIPTION = 'print information about a backup'
    USAGE = dedent("""
        Usage:
            emborg [options] info

        Options:
            -f, --fast            only report local information
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        fast = cmdline['--fast']
        src_dirs = (str(d) for d in settings.src_dirs)
        output(f'              config: {settings.config_name}')
        output(f'              source: {", ".join(src_dirs)}')
        output(f'         destination: {settings.destination()}')
        output(f'  settings directory: {settings.config_dir}')
        output(f'              logile: {settings.logfile}')
        try:
            backup_date = arrow.get(settings.date_file.read_text())
            output(f'      last backed up: {backup_date}, {backup_date.humanize()}')
        except FileNotFoundError as e:
            narrate(os_error(e))
        except arrow.parser.ParserError as e:
            narrate(e, culprit=settings.date_file)
        if fast:
            return

        # now output the info from our borg repository
        borg = settings.run_borg(
            cmd = 'info',
            args = [settings.destination()],
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output()
            output(out.rstrip())


# Initialize command {{{1
class Initialize(Command):
    NAMES = 'init'.split()
    DESCRIPTION = 'initialize the repository'
    USAGE = dedent("""
        Usage:
            emborg init
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        # run borg
        borg = settings.run_borg(
            cmd = 'init',
            args = [settings.destination()],
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# List command {{{1
class List(Command):
    NAMES = 'list lr archives'.split()
    DESCRIPTION = 'list the archives currently contained in the repository'
    USAGE = dedent("""
        Usage:
            emborg list
            emborg archives
            emborg lr
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        # run borg
        borg = settings.run_borg(
            cmd = 'list',
            args = ['--short', settings.destination()],
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# Log command {{{1
class Log(Command):
    NAMES = 'log'.split()
    DESCRIPTION = 'print logfile for the last emborg run'
    USAGE = dedent("""
        Usage:
            emborg log
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        try:
            prev_log = settings.prev_logfile.read_text()
            output(prev_log)
        except FileNotFoundError as e:
            narrate(os_error(e))


# Manifest command {{{1
class Manifest(Command):
    NAMES = 'manifest m la'.split()
    DESCRIPTION = 'list the files contained in an archive'
    USAGE = dedent("""
        Usage:
            emborg [options] manifest
            emborg [options] m
            emborg [options] la

        Options:
            -d <date>, --date <date>            date of the desired version of paths
            -a <archive>, --archive <archive>   name of the archive to use
            -n, --name                          output only the filename

        Once a backup has been performed, you can list the files available in
        your archive using:

            emborg manifest

        This lists the files in the most recent archive. You can explicitly
        specify a particular archive if you wish:

            emborg manifest --archive kundert-2018-12-05T12:54:26

        Or you choose an archive based on a date. The first archive that was
        created after the specified date is used:

            emborg manifest --date 2015/04/01
            emborg manifest --date 2015-04-01
            emborg manifest --date 2018-12-05T12:39
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        archive = cmdline['--archive']
        date = cmdline['--date']
        filenames_only = cmdline['--name']

        # get the desired archive
        if date and not archive:
            archive = get_nearest_archive(settings, date)
            if not archive:
                raise Error('archive not available.', culprit=date)
        if not archive:
            archives = get_available_archives(settings)
            if not archives:
                raise Error('no archives are available.')
            archive = archives[-1]['name']
        output('Archive:', archive)

        # run borg
        list_opts = ['--short'] if filenames_only else []
        borg = settings.run_borg(
            cmd = 'list',
            args = list_opts + [settings.destination(archive)],
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# Mount command {{{1
class Mount(Command):
    NAMES = 'mount'.split()
    DESCRIPTION = 'mount a repository or archive'
    USAGE = dedent("""
        Usage:
            emborg [options] mount <mount_point>

        Options:
            -d <date>, --date <date>            date of the desired version of paths
            -a <archive>, --archive <archive>   name of the archive to use

        You can mount a repository or archive using:

            emborg mount backups

        If the specified mount point (backups in this example) exists in the
        current directory, it must be a directory. If it does not exist, it is
        created.

        If you do not specify an archive or date, all archives are mounted.

        You can mount an archive that existed on a particular date using:

            emborg mount --date 2015-04-01 backups

        Or, you can mount a particular archive using:

            emborg mount --archive kundert-2018-12-05T12:54:26 backups

        You should use `emborg umount` when you are done.
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        mount_point = cmdline['<mount_point>']
        archive = cmdline['--archive']
        date = cmdline['--date']

        # get the desired archive
        if date and not archive:
            archive = get_nearest_archive(settings, date)
            if not archive:
                raise Error('archive not available.', culprit=date)

        # create mount point if it does not exist
        try:
            mkdir(mount_point)
        except OSError as e:
            raise Error(os_error(e))

        # run borg
        borg = settings.run_borg(
            cmd = 'mount',
            args = [settings.destination(archive), mount_point],
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# Prune command {{{1
class Prune(Command):
    NAMES = 'prune'.split()
    DESCRIPTION = 'list the archives currently contained in the repository'
    USAGE = dedent("""
        Usage:
            emborg prune
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        # checking the settings
        intervals = 'within last minutely hourly daily weekly monthly yearly'
        prune_settings = [('keep_' + s) for s in intervals.split()]
        if not any(settings.value(s) for s in prune_settings):
            prune_settings = conjoin(prune_settings, ', or ')
            raise Error(
                'No prune settings available',
                codicil=f'At least one of {prune_settings} must be specified.'
            )

        # run borg
        borg = settings.run_borg(
            cmd = 'prune',
            args = [settings.destination()],
            emborg_opts = options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# Settings command {{{1
class Settings(Command):
    NAMES = 'settings'.split()
    DESCRIPTION = 'list settings of chosen configuration'
    USAGE = dedent("""
        Usage:
            emborg [options] settings

        Options:
            -a, --available   list available settings
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        show_available = cmdline['--available']
        unknown = Color('yellow')
        known = Color('cyan')

        if show_available:
            output('Emborg settings:')
            for name, desc in EMBORG_SETTINGS.items():
                output(f'{known(name):>33s}: {desc}')

            output()
            output('Borg settings:')
            for name, attrs in BORG_SETTINGS.items():
                output(f"{known(name):>33s}: {attrs['desc']}")
            return

        for k, v in settings:
            is_known = k in EMBORG_SETTINGS or k in BORG_SETTINGS
            key = known(k) if is_known else unknown(k)
            if k == 'passphrase':
                v = '<set>'
            output(f'{key:>33}: {render(v, level=6)}')


# Umount command {{{1
class Umount(Command):
    NAMES = 'umount unmount'.split()
    DESCRIPTION = 'un-mount a previously mounted repository or archive'
    USAGE = dedent("""
        Usage:
            emborg [options] umount <mount_point>
            emborg [options] unmount <mount_point>
    """).strip()
    REQUIRES_EXCLUSIVITY = True

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        mount_point = cmdline['<mount_point>']

        # run borg
        try:
            settings.run_borg(
                cmd = 'umount',
                args = [mount_point],
                emborg_opts = options,
            )
        except Error as e:
            if 'busy' in str(e):
                e.reraise(
                    codicil=f"Try running 'lsof +D {mount_point}' to find culprit."
                )


# Version {{{1
class Version(Command):
    NAMES = 'version',
    DESCRIPTION = 'display emborg version'
    USAGE = dedent("""
        Usage:
            emborg version
    """).strip()
    REQUIRES_EXCLUSIVITY = False

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        # get the Python version
        python = 'Python %s.%s.%s' % (
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        )

        # output the Avendesora version along with the Python version
        from .__init__ import __version__, __released__
        output('emborg version: %s (%s) [%s].' % (
            __version__, __released__, python
        ))
