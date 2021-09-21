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
# along with this program.  If not, see http://www.gnu.org/licenses.


# Imports {{{1
import json
import os
import sys
from textwrap import dedent, fill
import arrow
from docopt import docopt
from inform import (
    Color,
    Error,
    comment,
    conjoin,
    display,
    full_stop,
    indent,
    is_str,
    join,
    log,
    narrate,
    os_error,
    output,
    render,
    title_case,
    warn,
)
from quantiphy import Quantity, UnitConversion, QuantiPhyError
from shlib import (
    Run, cwd, mkdir, rm, set_prefs as set_shlib_prefs, split_cmd, to_path
)
from time import sleep
from .collection import Collection
from .preferences import BORG_SETTINGS, DEFAULT_COMMAND, EMBORG_SETTINGS, PROGRAM_NAME
from .utilities import gethostname, two_columns


# Utilities {{{1
hostname = gethostname()
set_shlib_prefs(use_inform=True, log_cmd=True)


# time conversions {{{2
UnitConversion('s', 'sec second seconds')
UnitConversion('s', 'm min minute minutes', 60)
UnitConversion('s', 'h hr hour hours', 60*60)
UnitConversion('s', 'd day days', 24*60*60)
UnitConversion('s', 'w week weeks', 7*24*60*60)
UnitConversion('s', 'M month months', 30*24*60*60)
UnitConversion('s', 'y year years', 365*24*60*60)
Quantity.set_prefs(ignore_sf=True)

# title() {{{2
def title(text):
    return full_stop(title_case(text))


# get_available_archives() {{{2
def get_available_archives(settings):
    # run borg
    borg = settings.run_borg(cmd="list", args=["--json", settings.destination()])
    try:
        data = json.loads(borg.stdout)
        return data["archives"]
    except json.decoder.JSONDecodeError as e:
        raise Error("Could not decode output of Borg list command.", codicil=e)


# get_name_of_latest_archive() {{{2
def get_name_of_latest_archive(settings):
    archives = get_available_archives(settings)
    if not archives:
        raise Error("no archives are available.")
    if archives:
        return archives[-1]["name"]


def get_name_of_nearest_archive(settings, date):
    archives = get_available_archives(settings)
    try:
        target = arrow.get(date, tzinfo='local')
    except arrow.parser.ParserError as e:
        try:
            seconds = Quantity(date, 'd', scale='s')
            target = arrow.now().shift(seconds=-seconds)
        except QuantiPhyError:
            codicil = join(
                full_stop(e),
                'Alternatively relative time formats are accepted:',
                'Ns, Nm, Nh, Nd, Nw, NM, Ny.  Example 2w is 2 weeks.'
            )
            raise Error(
                "invalid date specification.",
                culprit=date, codicil=codicil, wrap=True
            )

    # find oldest archive that is younger than specified target
    archive = prev_archive = None
    for archive in reversed(archives):
        archive_time = arrow.get(archive["time"], tzinfo='local')
        if archive_time <= target:
            if prev_archive:
                return prev_archive["name"]
            warn(
                f'archive younger than {date} ({target.humanize()}) was not found.',
                codicil='Using youngest that is older than given date and time.'
            )
            return archive["name"]
        prev_archive = archive
    if archive:
        warn(
            f'archive older than {date} ({target.humanize()}) was not found.',
            codicil='Using oldest available.'
        )
        return archive["name"]
    raise Error(
        f"no archive available is older than {date} ({target.humanize()})."
    )


# get_available_files() {{{2
def get_available_files(settings, archive):
    # run borg
    borg = settings.run_borg(
        cmd="list", args=["--json-lines", settings.destination(archive)],
    )
    try:
        files = []
        for line in borg.stdout.splitlines():
            files.append(json.loads(line))
        return files
    except json.decoder.JSONDecodeError as e:
        raise Error("Could not decode output of Borg list command.", codicil=e)

# get_archive_paths() {{{2
def get_archive_paths(paths, settings):
    # need to construct a path to the file that is compatible with those
    # paths stored in borg, thus it must begin with a src_dir (cannot just
    # use the absolute path because the corresponding src_dir path may
    # contain a symbolic link, in which the absolute path would not be found
    # in the borg repository
    # convert to paths relative to the working directory
    #
    paths_not_found = set(paths)
    resolved_paths = []
    roots = settings.resolve_patterns([], skip_checks=True)
    try:
        for root_dir in settings.roots:
            resolved_root_dir = root_dir.resolve()
            for name in paths:
                path = to_path(name)
                resolved_path = path.resolve()
                try:
                    # get relative path from root_dir to path after resolving
                    # symbolic links in both root_dir and path
                    path = resolved_path.relative_to(resolved_root_dir)

                    # add original root_dir (with sym links) to relative path
                    path = to_path(settings.working_dir, root_dir, path)

                    # get relative path from working dir to computed path
                    # this will be the path contained in borg archive
                    path = path.relative_to(settings.working_dir)

                    resolved_paths.append(path)
                    paths_not_found.remove(name)
                except ValueError as e:
                    pass
        if paths_not_found:
            raise Error(
                'not contained in a source directory:',
                conjoin(paths_not_found)
            )
        return resolved_paths
    except ValueError as e:
        raise Error(e)


# get_archive_path() {{{2
def get_archive_path(path, settings):
    paths = get_archive_paths([path], settings)
    assert len(paths) == 1
    return paths[0]


# Command base class {{{1
class Command:
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "error"
    # possible values are:
    #     'error': emit error if applied to composite config
    #     'all'  : use all configs of composite config in sequence
    #     'first': only use the first config in a composite config
    #     'none' : do not use any of configs in composite config
    SHOW_CONFIG_NAME = True

    @classmethod
    def commands(cls):
        for cmd in cls.__subclasses__():
            if hasattr(cmd, "NAMES"):
                yield cmd
            for sub in cmd.commands():
                if hasattr(sub, "NAMES"):
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
        raise Error("unknown command.", culprit=name)

    @classmethod
    def execute_early(cls, name, args, settings, options):
        # execute_early() takes same arguments as run(), but is run before the
        # settings files have been read.  As such, the settings argument is None.
        # run_early() is used for commands that do not need settings and should
        # work even if the settings files do not exist or are not valid.
        if hasattr(cls, "run_early"):
            narrate("running {} pre-command".format(name))
            return cls.run_early(name, args if args else [], settings, options)

    @classmethod
    def execute(cls, name, args, settings, options):
        if hasattr(cls, "run"):
            narrate("running {} command".format(name))
            exit_status = cls.run(name, args if args else [], settings, options)
            return 0 if exit_status is None else exit_status

    @classmethod
    def execute_late(cls, name, args, settings, options):
        # execute_late() takes same arguments as run(), but is run after all the
        # configurations have been run.  As such, the settings argument is None.
        # run_late() is used for commands that want to create a summary that
        # includes the results from all the configurations.
        if hasattr(cls, "run_late"):
            narrate("running {} post-command".format(name))
            return cls.run_late(name, args if args else [], settings, options)

    @classmethod
    def summarize(cls, width=16):
        summaries = []
        for cmd in Command.commands_sorted():
            summaries.append(two_columns(", ".join(cmd.NAMES), cmd.DESCRIPTION))
        return "\n".join(summaries)

    @classmethod
    def get_name(cls):
        return cls.NAMES[0]

    @classmethod
    def help(cls):
        text = dedent(
            """
            {title}

            {usage}
            """
        ).strip()

        return text.format(title=title(cls.DESCRIPTION), usage=cls.USAGE,)


# BorgCommand command {{{1
class BorgCommand(Command):
    NAMES = "borg".split()
    DESCRIPTION = "run a raw borg command."
    USAGE = dedent(
        """
        Usage:
            emborg borg <borg_args>...

        An argument that is precisely '@repo' is replaced with the path to the
        repository.  The passphrase is set before the command is run.
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "error"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args, options_first=True)
        borg_args = cmdline["<borg_args>"]

        # run borg
        borg = settings.run_borg_raw(borg_args)
        out = borg.stdout
        if out:
            output(out.rstrip())


# BreakLockCommand command {{{1
class BreakLockCommand(Command):
    NAMES = "breaklock break-lock".split()
    DESCRIPTION = "breaks the repository and cache locks."
    USAGE = dedent(
        """
        Usage:
            emborg breaklock
            emborg break-lock

        Breaks both the local and the repository locks.  Be sure Borg is no
        longer running before using this command.
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = False
    COMPOSITE_CONFIGS = "error"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        # run borg
        borg = settings.run_borg(
            cmd="break-lock", args=[settings.destination()], emborg_opts=options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())
        rm(settings.lockfile)


# CheckCommand command {{{1
class CheckCommand(Command):
    NAMES = "check".split()
    DESCRIPTION = "checks the repository and its archives"
    USAGE = dedent(
        """
        Usage:
            emborg check [options] [<archive>]

        Options:
            -A, --all                           check all available archives
            -e, --include-external              check all archives in repository, not just
                                                those associated with this configuration
            -r, --repair                        attempt to repair any inconsistencies found
            -v, --verify-data                   perform a full integrity verification (slow)

        The most recently created archive is checked if one is not specified
        unless --all is given, in which case all archives are checked.
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "all"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        archive = cmdline["<archive>"]
        check_all = cmdline["--all"]
        include_external_archives = cmdline["--include-external"]
        verify = ["--verify-data"] if cmdline["--verify-data"] else []
        repair = ['--repair'] if cmdline['--repair'] else []
        if repair:
            os.environ['BORG_CHECK_I_KNOW_WHAT_I_AM_DOING'] = 'YES'

        # identify archive or archives to check
        if check_all:
            archive = None
        elif not archive:
            archive = get_name_of_latest_archive(settings)

        # run borg
        borg = settings.run_borg(
            cmd = "check",
            args = verify + repair + [settings.destination(archive)],
            emborg_opts = options,
            strip_prefix = include_external_archives,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# CompareCommand command {{{1
class CompareCommand(Command):
    NAMES = "compare".split()
    DESCRIPTION = "compare local files or directories to those in an archive"
    USAGE = dedent(
        """
        Usage:
            emborg [options] compare [<path>]

        Options:
            -a <archive>, --archive <archive>   name of the archive to mount
            -d <date>, --date <date>            date of the desired archive
            -i, --interactive                   perform an interactive comparison


        Reports and allows you to manage the differences between your local
        files and those in an archive.  The base command simply reports the
        differences:

            $ emborg compare

        The --interactive option allows you to manage those differences.
        Specifically, it will open an interactive file comparison tool that
        allows you to compare the contents of your files and copy differences
        from the files in the archive to your local files:

            $ emborg compare -i

        You can specify the archive by name or by date or age.  If you do not
        you will use the most recent archive:

            $ emborg compare -a continuum-2020-12-04T17:41:28
            $ emborg compare -d 2020-12-04
            $ emborg compare -d 1w

        You can specify a path to a file or directory to compare, if you do not
        you will compare the files and directories of the current working
        directory.

            $ emborg compare tests
            $ emborg compare ~/bin

        This command requires that the following settings be specified in your
        settings file: manage_diffs_cmd, report_diffs_cmd, and
        default_mount_point.

        The command operates by mounting the desired archive, performing the
        comparison, and then unmounting the directory.  Problems sometimes occur
        that can result in the archive remaining mounted.  In this case you will
        need to resolve any issues that are preventing the unmounting, and then
        explicitly run the :ref:`unmount command <umount>` before you can use
        this *Borg* repository again.

        This command differs from the :ref:`diff command <diff>` in that it
        compares local files to those in an archive where as :ref:`diff <diff>`
        compares the files contained in two archives.
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "first"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        mount_point = settings.as_path("default_mount_point")
        if not mount_point:
            raise Error("must specify default_mount_point setting to use this command.")
        path = cmdline['<path>']
        archive = cmdline["--archive"]
        date = cmdline["--date"]

        # get the desired archive
        if not archive:
            if date:
                archive = get_name_of_nearest_archive(settings, date)
            else:
                archive = get_name_of_latest_archive(settings)
            display(f'Using {archive}.')

        # get diff tool
        if cmdline['--interactive']:
            differ = settings.manage_diffs_cmd
            if not differ:
                narrate("manage_diffs_cmd not set, trying report_diffs_cmd.")
                differ = settings.report_diffs_cmd
        else:
            differ = settings.report_diffs_cmd
            if not differ:
                narrate("report_diffs_cmd not set, trying manage_diffs_cmd.")
                differ = settings.manage_diffs_cmd
        if not differ:
            raise Error("no diff command available.")

        # resolve the path relative to working directory
        if not path:
            path = '.'
        arch_path = to_path(path).resolve().relative_to(settings.working_dir)
        arch_path = to_path(mount_point, arch_path)

        # create mount point if it does not exist
        try:
            mkdir(mount_point)
        except OSError as e:
            raise Error(os_error(e))

        # run borg to mount
        borg = settings.run_borg(
            cmd = "mount",
            args = [settings.destination(archive), mount_point],
            emborg_opts = options,
        )

        try:
            # run diff tool
            diff_cmd = differ.format(path, arch_path)
            if diff_cmd == differ:
                diff_cmd = f"{differ} '{path}' '{arch_path}'"
            diff = Run(diff_cmd, 'SoeW1')

        finally:
            # run borg to un-mount
            sleep(0.25)
            settings.run_borg(
                cmd="umount", args=[mount_point], emborg_opts=options,
            )
            try:
                mount_point.rmdir()
            except OSError as e:
                warn(os_error(e), codicil="You will need to unmount before proceeding.")

        return diff.status


# ConfigsCommand command {{{1
class ConfigsCommand(Command):
    NAMES = "configs".split()
    DESCRIPTION = "list available backup configurations"
    USAGE = dedent(
        """
        Usage:
            emborg configs
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = False
    COMPOSITE_CONFIGS = "none"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        configs = Collection(settings.configurations)
        if configs:
            output("Available Configurations:", *configs, sep="\n    ")
        else:
            output("No configurations available.")

        output()

        default_config = settings.default_configuration
        if default_config:
            output("Default Configuration:", default_config, sep="\n    ")
        else:
            output("No default configuration available.")


# CreateCommand command {{{1
class CreateCommand(Command):
    NAMES = "create backup".split()
    DESCRIPTION = "create an archive of the current files"
    USAGE = dedent(
        """
        Usage:
            emborg create [options]
            emborg backup [options]

        Options:
            -f, --fast       skip pruning and checking for a faster backup on a slow network
            -l, --list       list the files and directories as they are processed
            -p, --progress   shows Borg progress
            -s, --stats      show Borg statistics

        To see the files listed as they are backed up, use the Emborg -v option.
        This can help you debug slow create operations.
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "all"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        borg_opts = []
        if cmdline["--stats"] or settings.show_stats:
            borg_opts.append("--stats")
        if cmdline["--list"]:
            borg_opts.append("--list")
        if cmdline["--progress"] or settings.show_progress:
            borg_opts.append("--progress")
            announce = display
        else:
            announce = narrate

        # check the dependencies are available
        must_exist = settings.as_paths("must_exist")
        for path in must_exist:
            if not path.exists():
                raise Error(
                    "does not exist, perform setup and restart.",
                    culprit = ("must_exist", path),
                )

        # run prerequisites
        if settings.is_first_config():
            pre_script_settings = ["run_before_first_backup", "run_before_backup"]
        else:
            pre_script_settings = ["run_before_backup"]
        for setting in pre_script_settings:
            for i, cmd in enumerate(settings.values(setting)):
                narrate(f"staging {setting}[{i}] pre-backup script")
                try:
                    Run(cmd, "SoEW")
                except Error as e:
                    e.reraise(culprit=(setting, cmd.split()[0]))

        # run borg
        src_dirs = settings.src_dirs
        settings.hooks.backups_begin()
        try:
            borg = settings.run_borg(
                cmd = "create",
                borg_opts = borg_opts,
                args = [settings.destination(True)] + src_dirs,
                emborg_opts = options,
                show_borg_output = bool(borg_opts),
                use_working_dir = True,
            )
        except Error as e:
            if e.stderr and "is not a valid repository" in e.stderr:
                e.reraise(codicil="Run 'emborg init' to initialize the repository.")
            else:
                raise
        settings.hooks.backups_finish(borg)

        # update the date files
        narrate("update date file")
        now = arrow.now()
        settings.date_file.write_text(str(now))



        # run scripts specified to be run after a backup
        if settings.is_last_config():
            post_script_settings = ["run_after_backup", "run_after_last_backup"]
        else:
            post_script_settings = ["run_after_backup"]
        for setting in post_script_settings:
            for i, cmd in enumerate(settings.values(setting)):
                narrate(f"staging {setting}[{i}] post-backup script")
                try:
                    Run(cmd, "SoEW")
                except Error as e:
                    e.reraise(culprit=(setting, cmd.split()[0]))

        if cmdline["--fast"]:
            return

        # check and prune the archives if requested
        try:
            # check the archives if requested
            activity = "checking"
            if settings.check_after_create:
                announce("Checking archive ...")
                if settings.check_after_create == "latest":
                    args = []
                elif settings.check_after_create in [True, "all"]:
                    args = ["--all"]
                elif settings.check_after_create == "all in repository":
                    args = ["--all", "--include-external"]
                else:
                    warn(
                        "unknown value: {}, checking latest.".format(
                            settings.check_after_create
                        ),
                        cuplrit = "check_after_create",
                    )
                    args = []
                check = CheckCommand()
                check.run("check", args, settings, options)

            activity = "pruning"
            if settings.prune_after_create:
                announce("Pruning archives ...")
                prune = PruneCommand()
                args = ["--stats"] if cmdline["--stats"] else []
                prune.run("prune", args, settings, options)
        except Error as e:
            e.reraise(
                codicil = (
                    f"This error occurred while {activity} the archives.",
                    "No error was reported while creating the archive.",
                )
            )


# DeleteCommand command {{{1
class DeleteCommand(Command):
    NAMES = "delete".split()
    DESCRIPTION = "delete an archive currently contained in the repository"
    USAGE = dedent(
        """
        Usage:
            emborg [options] delete [<archive>]

        Options:
            -r, --repo     delete entire repository
            -s, --stats    show Borg statistics

        If no archive is specified, the latest is deleted.
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "error"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        archive = cmdline["<archive>"]
        if cmdline['--repo']:
            if archive:
                raise Error("must not specify an archive along with --repo.")
            os.environ['BORG_DELETE_I_KNOW_WHAT_I_AM_DOING'] = 'YES'
        else:
            if not archive:
                archive = get_name_of_latest_archive(settings)
                if not archive:
                    raise Error("no archives available.")
        show_stats = cmdline["--stats"] or settings.show_stats

        # run borg
        borg = settings.run_borg(
            cmd = "delete",
            args = [settings.destination(archive)],
            emborg_opts = options,
            strip_prefix = True,
            show_borg_output = show_stats,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# DiffCommand command {{{1
class DiffCommand(Command):
    NAMES = "diff".split()
    DESCRIPTION = "show the differences between two archives"
    USAGE = dedent(
        """
        Usage:
            emborg diff [options] <archive1> <archive2> [<path>]

        Options:
            -R, --recursive                     show files in sub directories
                                                when path is specified
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "error"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        archive1 = cmdline["<archive1>"]
        archive2 = cmdline["<archive2>"]
        path = cmdline['<path>']
        recursive = cmdline['--recursive']

        # resolve the path relative to working directory
        if path:
            path = str(get_archive_path(path, settings))
        else:
            path = ''

        # run borg
        borg = settings.run_borg(
            cmd = "diff",
            args = [settings.destination(archive1), archive2],
            emborg_opts = options,
            borg_opts = ['--json-lines'],
        )

        # convert from JSON-lines to JSON
        json_data = '[' + ','.join(borg.stdout.splitlines()) + ']'
        diffs = json.loads(json_data)

        for diff in diffs:
            this_path = diff['path']
            if path:
                if not this_path.startswith(path):
                    continue  # skip files not on the path
                if not recursive:
                    if '/' in this_path[len(path)+1:]:
                        continue  # skip files is subdirs of specified path
            changes = diff['changes'][0]
            type = changes.get('type', '')
            if 'size' in changes:
                size = Quantity(changes['size'], 'B').render(prec=3)
            else:
                size = ''
            num_spaces = max(19 - len(type) - len(size), 1)
            sep = num_spaces * ' '
            desc = type + sep + size
            print(desc, this_path)

        return 1 if diffs else 0


# DueCommand command {{{1
class DueCommand(Command):
    NAMES = "due".split()
    DESCRIPTION = "days since last backup"
    USAGE = dedent(
        """
        Used with status bar programs, such as i3status, to make user aware that
        backups are due.

        Usage:
            emborg due [options]

        Options:
            -d <num>, --days <num>     emit message if this many days have passed
                                       since last backup
            -e <addr>, --email <addr>  send email message rather than print message
            -m <msg>, --message <msg>  the message to emit
            -o, --oldest               with composite configuration, only report
                                       the oldest

        If you specify the days, then the message is only printed if the backup
        is overdue.  If not overdue, nothing is printed.  The message is always
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
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = False
    COMPOSITE_CONFIGS = "all"
    MESSAGES = {}
    SHOW_CONFIG_NAME = False
    OLDEST_DATE = None
    OLDEST_CONFIG = None

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        email = cmdline["--email"]

        def gen_message(date):
            if cmdline["--message"]:
                since_last_backup = arrow.now() - date
                days = since_last_backup.total_seconds() / 86400
                elapsed = date.humanize(only_distance=True)
                try:
                    return cmdline["--message"].format(
                        days=days, elapsed=elapsed, config=settings.config_name
                    )
                except KeyError as e:
                    raise Error(
                        "unknown key in:",
                        culprit = e.args[0],
                        codicil = cmdline["--message"],
                    )
            else:
                return f"The latest {settings.config_name} archive was created {date.humanize()}."

        if email:

            def save_message(msg):
                cls.MESSAGES[settings.config_name] = dedent(
                    f"""
                    {msg}
                    config = {settings.config_name}
                    source host = {hostname}
                    source directories = {', '.join(str(d) for d in settings.src_dirs)}
                    destination = {settings.repository}
                    """
                ).lstrip()

        else:

            def save_message(msg):
                cls.MESSAGES[settings.config_name] = msg

        # Get date of last backup
        date_file = settings.date_file
        try:
            backup_date = arrow.get(date_file.read_text())
        except FileNotFoundError:
            backup_date = arrow.get("19560105", "YYYYMMDD")
        except arrow.parser.ParserError:
            raise Error("date not given in iso format.", culprit=date_file)

        # Record the name of the oldest config
        if not cls.OLDEST_DATE or backup_date < cls.OLDEST_DATE:
            cls.OLDEST_DATE = backup_date
            cls.OLDEST_CONFIG = settings.config_name

        # Warn user if backup is overdue
        if cmdline.get("--days"):
            since_last_backup = arrow.now() - backup_date
            days = since_last_backup.total_seconds() / 86400
            try:
                if days > float(cmdline["--days"]):
                    save_message(gen_message(backup_date))
                    if not email:
                        return 1
            except ValueError:
                raise Error("expected a number for --days.")
            return

        # Otherwise, simply report age of backups
        save_message(gen_message(backup_date))

    @classmethod
    def run_late(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        email = cmdline["--email"]

        if not cls.MESSAGES:
            return

        if cmdline["--oldest"]:
            message = cls.MESSAGES[cls.OLDEST_CONFIG]
        else:
            message = "\n".join(cls.MESSAGES.values())

        if email:
            Run(
                ["mail", "-s", f"{PROGRAM_NAME}: backup is overdue", email],
                stdin = message,
                modes = "soeW",
            )
        else:
            output(message)


# ExtractCommand command {{{1
class ExtractCommand(Command):
    NAMES = "extract".split()
    DESCRIPTION = "recover file or files from archive"
    USAGE = dedent(
        """
        Usage:
            emborg [options] extract <path>...

        Options:
            -a <archive>, --archive <archive>   name of the archive to use
            -d <date>, --date <date>            date of the desired version of paths
            -f, --force                         extract even if it might overwrite
                                                the original file
            -l, --list                          list the files and directories as
                                                they are processed

        You extract a file or directory using:

            emborg extract home/ken/src/avendesora/doc/overview.rst

        The path or paths given should match those found in the Borg archive.
        Use manifest to determine what path you should specify (the paths are
        relative to the working directory, which defaults to / but can be
        overridden in a configuration file).  The paths may point to
        directories, in which case the entire directory is extracted.

        By default, the most recent archive is used, however, if desired you can
        explicitly specify a particular archive.  For example:

            $ emborg extract --archive continuum-2020-12-05T12:54:26 home/shaunte/bin

        Alternatively you can specify a date or date and time.  If only the date
        is given the time is taken to be midnight.  The oldest archive that is
        younger than specified date and time is used.

            $ emborg extract --date 2021-04-01 home/shaunte/bin
            $ emborg extract --date 2021-04-01T15:30 home/shaunte/bin

        Alternatively, you can specify the date and time in relative terms:

            $ emborg extract --date 3d  home/shaunte/bin

        In this case 3d means 3 days.  You can use s, m, h, d, w, M, and y to
        represent seconds, minutes, hours, days, weeks, months, and years.

        The extracted files are placed in the current working directory with
        the original hierarchy.  Thus, the above commands create the file:

            ./home/ken/src/avendesora/doc/overview.rst

        Normally, extract refuses to run if your current directory is the
        working directory used by Emborg so as to avoid overwriting an existing
        file.  If your intent is to overwrite the existing file, you can specify
        the --force option.  Or, consider using the restore command; it
        overwrites the existing file regardless of what directory you run from.

        This command is very similar to the restore command except that it uses
        paths as they are given in the archive and so need not extract the files
        into their original location.
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "first"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        paths = cmdline["<path>"]
        archive = cmdline["--archive"]
        date = cmdline["--date"]
        borg_opts = []
        if cmdline["--list"]:
            borg_opts.append("--list")
        if not cmdline["--force"]:
            if cwd().samefile(settings.working_dir):
                raise Error(
                    "Running from the working directory risks",
                    "over writing the existing file or files. ",
                    "Use --force if this is desired.",
                    wrap = True,
                )

        # convert absolute paths to paths relative to the working directory
        paths = [to_path(p) for p in paths]
        try:
            paths = [
                p.relative_to(settings.working_dir) if p.is_absolute() else p
                for p in paths
            ]
        except ValueError as e:
            raise Error(e)

        # get the desired archive
        if date and not archive:
            archive = get_name_of_nearest_archive(settings, date)
        if not archive:
            archive = get_name_of_latest_archive(settings)
        display("Archive:", archive)

        # run borg
        borg = settings.run_borg(
            cmd = "extract",
            borg_opts = borg_opts,
            args = [settings.destination(archive)] + paths,
            emborg_opts = options,
            show_borg_output = bool(borg_opts),
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# HelpCommand {{{1
class HelpCommand(Command):
    NAMES = "help".split()
    DESCRIPTION = "give information about commands or other topics"
    USAGE = dedent(
        """
        Usage:
            emborg help [<topic>]
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = False
    COMPOSITE_CONFIGS = "none"

    @classmethod
    def run_early(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)

        from .help import HelpMessage

        HelpMessage.show(cmdline["<topic>"])
        return 0


# InfoCommand command {{{1
class InfoCommand(Command):
    NAMES = "info".split()
    DESCRIPTION = "print information about a backup"
    USAGE = dedent(
        """
        Usage:
            emborg [options] info

        Options:
            -f, --fast               only report local information
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "all"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        fast = cmdline["--fast"]

        # run borg_options('create') to populate settings.roots
        try:
            settings.borg_options('create', None, (), False)
            roots = (str(r) for r in settings.roots)
        except Error:
            roots = ['not set']

        # report local information
        output(f"              config: {settings.config_name}")
        output(f'               roots: {", ".join(roots)}')
        output(f"         destination: {settings.destination()}")
        output(f"  settings directory: {settings.config_dir}")
        output(f"             logfile: {settings.logfile}")
        try:
            backup_date = arrow.get(settings.date_file.read_text())
            output(f"      last backed up: {backup_date}, {backup_date.humanize()}")
        except FileNotFoundError as e:
            narrate(os_error(e))
        except arrow.parser.ParserError as e:
            narrate(e, culprit=settings.date_file)
        if fast:
            return

        # now output the information from borg about the repository
        borg = settings.run_borg(
            cmd = "info",
            args = [settings.destination()],
            emborg_opts = options,
            strip_prefix = True,
        )
        out = borg.stdout
        if out:
            output()
            output(out.rstrip())


# InitializeCommand command {{{1
class InitializeCommand(Command):
    NAMES = "init".split()
    DESCRIPTION = "initialize the repository"
    USAGE = dedent(
        """
        Usage:
            emborg init
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "all"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        # run borg
        borg = settings.run_borg(
            cmd="init", args=[settings.destination()], emborg_opts=options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# ListCommand command {{{1
class ListCommand(Command):
    NAMES = "list lr archives".split()
    DESCRIPTION = "list the archives currently contained in the repository"
    USAGE = dedent(
        """
        Usage:
            emborg [options] list
            emborg [options] archives
            emborg [options] lr

        Options:
            -e, --include-external   list all archives in repository, not just
                                     those associated with this configuration
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "first"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        include_external_archives = cmdline["--include-external"]

        # run borg
        borg = settings.run_borg(
            cmd = "list",
            args = ["--short", settings.destination()],
            emborg_opts = options,
            strip_prefix = include_external_archives,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# LogCommand command {{{1
class LogCommand(Command):
    NAMES = "log".split()
    DESCRIPTION = "print logfile for the last emborg run"
    USAGE = dedent(
        """
        Usage:
            emborg log
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = False
    COMPOSITE_CONFIGS = "all"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        docopt(cls.USAGE, argv=[command] + args)

        try:
            prev_log = settings.prev_logfile.read_text()
            output(prev_log)
        except FileNotFoundError as e:
            narrate(os_error(e))


# ManifestCommand command {{{1
class ManifestCommand(Command):
    NAMES = "manifest m la files f".split()
    DESCRIPTION = "list the files contained in an archive"
    USAGE = dedent(
        """
        Usage:
            emborg [options] manifest [<path>]
            emborg [options] m [<path>]
            emborg [options] la [<path>]
            emborg [options] files [<path>]
            emborg [options] f [<path>]

        Options:
            -a <archive>, --archive <archive>   name of the archive to use
            -c, --no-color                      do not color based on health
            -d <date>, --date <date>            date of the desired archive
            -s, --short                         use short listing format
            -l, --long                          use long listing format
            -n, --name                          use name only listing format
            -f <fmt>, --format <fmt>            use <fmt> listing format
            -F, --show-formats                  show available formats and exit
            -N, --sort-by-name                  sort by filename
            -D, --sort-by-date                  sort by date
            -S, --sort-by-size                  sort by size
            -O, --sort-by-owner                 sort by owner
            -G, --sort-by-group                 sort by group
            -K <name>, --sort-by-key <name>     sort by key (the Borg field name)
            -r, --reverse-sort                  reverse the sort order
            -R, --recursive                     show files in sub directories
                                                when path is specified

        Once a backup has been performed, you can list the files available in
        your archive using::

            emborg manifest

        This lists the files in the most recent archive.  If you specify the
        path, then the files listed are contained within that path.  For
        example::

            emborg manifest .

        This command lists the files in the archive that were originally
        contained in the current working directory.

        You can specify a particular archive if you wish:

            emborg manifest --archive kundert-2018-12-05T12:54:26

        Or you choose an archive based on a date and time.  The oldest archive
        that is younger than specified date and time is used.

            emborg manifest --date 2021/04/01
            emborg manifest --date 2021-04-01
            emborg manifest --date 2020-12-05T12:39

        You can also the date in relative terms using s, m, h, d, w, M, y to
        indicate seconds, minutes, hours, days, weeks, months, and years:

            emborg manifest --date 2w

        There are a variety of ways that you use to sort the output.  For
        example, sort by size, use:

            emborg manifest -S
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "first"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        path = cmdline["<path>"]
        archive = cmdline["--archive"]
        date = cmdline["--date"]
        recursive = cmdline["--recursive"]

        # resolve the path relative to working directory
        if path:
            path = str(get_archive_path(path, settings))
        else:
            path = ''

        # get the desired archive
        if date and not archive:
            archive = get_name_of_nearest_archive(settings, date)
        if not archive:
            archive = get_name_of_latest_archive(settings)

        # define available formats
        formats = dict(
            name = "{path}",
            short = "{path}{Type}",
            date = "{mtime} {path}{Type}",
            size = "{size:8} {path}{Type}",
            owner = "{user:8} {path}{Type}",
            group = "{group:8} {path}{Type}",
            long = '{mode:10} {user:6} {group:6} {size:8} {mtime} {path}{extra}',
        )
        default_format = settings.manifest_default_format
        if not default_format:
            default_format = 'short'
        user_formats = settings.manifest_formats
        if user_formats:
            unknown = user_formats.keys() - formats.keys()
            if unknown:
                warn("unknown formats:", ", ".join(unknown), culprit="manifest_formats")
            formats.update(user_formats)
        if cmdline["--show-formats"]:
            for k, v in formats.items():
                output(f'{k:>9}: {v!r}')
            output()
            output(f'default format: {default_format}')
            return

        # process sort options
        fmt = default_format
        sort_key = None
        if cmdline["--sort-by-name"]:
            fmt = "short"
            sort_key = 'path'
        elif cmdline["--sort-by-date"]:
            fmt = "date"
            sort_key = 'mtime'
        elif cmdline["--sort-by-size"]:
            fmt = "size"
            sort_key = 'size'
        elif cmdline["--sort-by-owner"]:
            fmt = "owner"
            sort_key = 'user'
        elif cmdline["--sort-by-group"]:
            fmt = "group"
            sort_key = 'group'
        elif cmdline["--sort-by-key"]:
            sort_key = cmdline["--sort-by-key"]

        # process format options
        if cmdline["--name"]:
            fmt = "name"
        elif cmdline["--long"]:
            fmt = "long"
        elif cmdline["--short"]:
            fmt = "short"
        if cmdline['--format']:
            fmt = cmdline['--format']
            if fmt not in formats:
                raise Error('unknown format.', culprit=fmt)

        # run borg
        output("Archive:", archive)
        template = formats.get(fmt)
        keys = template.lower()
            # lower case it so we get size when user requests Size
        if sort_key and '{' + sort_key not in keys:
            keys = keys + '{' + sort_key + '}'
        args = [
            settings.destination(archive),
            '--json-lines',
            '--format', keys,
        ]
        borg = settings.run_borg(
            cmd="list", args=args, emborg_opts=options,
        )
        # convert from JSON-lines to JSON
        json_data = '[' + ','.join(borg.stdout.splitlines()) + ']'
        lines = json.loads(json_data)

        # sort the output
        if sort_key:
            try:
                lines = sorted(lines, key=lambda x: x[sort_key])
            except KeyError:
                raise Error('unknown key.', culprit=sort_key)
        if cmdline["--reverse-sort"]:
            lines.reverse()

        # import QuantiPhy for Size
        Quantity.set_prefs(spacer="")

        # generate formatted output
        if cmdline['--no-color']:
            healthy_color = broken_color = lambda x: x
        else:
            healthy_color = Color("green", Color.isTTY())
            broken_color = Color("red", Color.isTTY())
        for values in lines:
            # this loop can be quite slow. the biggest issue is arrow. parsing
            # time is slow. also output() can be slow, so use print() instead.
            if path:
                if not values['path'].startswith(path):
                    continue  # skip files not on the path
                if not recursive:
                    if '/' in values['path'][len(path)+1:]:
                        continue  # skip files is subdirs of specified path
            if values['healthy']:
                colorize = healthy_color
            else:
                colorize = broken_color
            values['health'] = 'healthy' if values['healthy'] else 'broken'
            type = values['mode'][0]
            values['Type'] = ''
            values['extra'] = ''
            if type == 'd':
                values['Type'] = '/'  # directory
            elif type == 'l':
                values['Type'] = '@'  # directory
                values['extra'] = ' -> ' + values['source']
            elif type == 'h':
                values['extra'] = ' links to ' + values['source']
            elif type == 'p':
                values['Type'] = '|'
            elif type != '-':
                log('UNKNOWN TYPE:', type, values['path'])
            if 'mtime' in values and 'MTime' in template:
                values['MTime'] = arrow.get(values['mtime'])
            if 'ctime' in values and 'CTime' in template:
                values['CTime'] = arrow.get(values['ctime'])
            if 'atime' in values and 'ATime' in template:
                values['ATime'] = arrow.get(values['atime'])
            if 'size' in values and '{Size' in template:
                values['Size'] = Quantity(values['size'], "B")
            if 'csize' in values and '{CSize' in template:
                values['CSize'] = Quantity(values['csize'], "B")
            if 'dsize' in values and '{DSize' in template:
                values['DSize'] = Quantity(values['dsize'], "B")
            if 'dcsize' in values and '{DCSize' in template:
                values['DCSize'] = Quantity(values['dcsize'], "B")
            try:
                print(colorize(template.format(**values)))
            except ValueError as e:
                raise Error(
                    full_stop(e),
                    'Likely due to a bad format specification in manifest_formats:',
                    codicil=template
                )
            except KeyError as e:
                raise Error('Unknown key in:', culprit=e, codicil=template)


# MountCommand command {{{1
class MountCommand(Command):
    NAMES = "mount".split()
    DESCRIPTION = "mount a repository or archive"
    USAGE = dedent(
        """
        Usage:
            emborg [options] mount [<mount_point>]

        Options:
            -a <archive>, --archive <archive>   name of the archive to mount
            -A, --all                           mount all available archives
            -d <date>, --date <date>            date of the desired archive
            -e, --include-external              when mounting all archives, do
                                                not limit archives to only those
                                                associated with this configuration

        You can mount a repository or archive using:

            emborg mount backups

        If the specified mount point (backups in this example) exists in the
        current directory, it must be a directory.  If it does not exist, it is
        created.  If you do not specify a mount point, the value of the
        default_mount_point setting is used if provided.

        If you do not specify an archive or date, the most recently created
        archive is mounted.

        Or you choose an archive based on a date and time.  The oldest archive
        that is younger than specified date and time is used.

            emborg mount --date 2021-04-01 backups
            emborg mount --date 2021-04-01T18:30 backups

        You can also specify the date in relative terms::

            $ emborg mount --date 6M backups

        where s, m, h, d, w, M, and y represents seconds, minutes, hours, days,
        weeks, months, and years.

        You can mount a particular archive using:

            emborg mount --archive kundert-2018-12-05T12:54:26 backups

        Or, you can mount all available archives using:

            emborg mount --all backups

        You should use `emborg umount` when you are done.
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "first"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        mount_point = cmdline["<mount_point>"]
        if mount_point:
            mount_point = settings.to_path(mount_point, resolve=False)
        else:
            mount_point = settings.as_path("default_mount_point")
        if not mount_point:
            raise Error("must specify directory to use as mount point")
        display("mount point is:", mount_point)
        archive = cmdline["--archive"]
        date = cmdline["--date"]
        mount_all = cmdline["--all"]
        include_external_archives = cmdline["--include-external"]

        # get the desired archive
        if not archive:
            if date:
                archive = get_name_of_nearest_archive(settings, date)
            elif not mount_all:
                archive = get_name_of_latest_archive(settings)

        # create mount point if it does not exist
        try:
            mkdir(mount_point)
        except OSError as e:
            raise Error(os_error(e))

        # run borg
        borg = settings.run_borg(
            cmd = "mount",
            args = [settings.destination(archive), mount_point],
            emborg_opts = options,
            strip_prefix = include_external_archives,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# PruneCommand command {{{1
class PruneCommand(Command):
    NAMES = "prune".split()
    DESCRIPTION = "prune the repository of excess archives"
    USAGE = dedent(
        """
        Usage:
            emborg [options] prune

        Options:
            -e, --include-external   prune all archives in repository, not just
                                     those associated with this configuration
            -l, --list               show fate of each archive
            -s, --stats              show Borg statistics
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "all"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        include_external_archives = cmdline["--include-external"]
        borg_opts = []
        if cmdline["--stats"] or settings.show_stats:
            borg_opts.append("--stats")
        if cmdline["--list"]:
            borg_opts.append("--list")

        # checking the settings
        intervals = "within last minutely hourly daily weekly monthly yearly"
        prune_settings = [("keep_" + s) for s in intervals.split()]
        if not any(settings.value(s) for s in prune_settings):
            prune_settings = conjoin(prune_settings, ", or ")
            raise Error(
                "No prune settings available.",
                codicil = f"At least one of {prune_settings} must be specified.",
                wrap = True,
            )

        # run borg
        borg = settings.run_borg(
            cmd = "prune",
            borg_opts = borg_opts,
            args = [settings.destination()],
            emborg_opts = options,
            strip_prefix = include_external_archives,
            show_borg_output = bool(borg_opts),
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# RestoreCommand command {{{1
class RestoreCommand(Command):
    NAMES = "restore".split()
    DESCRIPTION = "Restore the given files or directories in place"
    USAGE = dedent(
        """
        Usage:
            emborg [options] restore <path>...

        Options:
            -a <archive>, --archive <archive>   name of the archive to use
            -d <date>, --date <date>            date of the desired version of paths
            -l, --list                          list the files and directories
                                                as they are processed

        The path or paths given are the paths on the local filesystem.  The
        corresponding paths in the archive are computed by assuming that the
        location of the files has not changed since the archive was created.
        The intent is to replace the files in place.

        By default, the most recent archive is used, however, if desired you can
        explicitly specify a particular archive.  For example:

            $ emborg restore --archive continuum-2020-12-05T12:54:26 resume.doc

        Or you choose an archive based on a date and time.  The oldest archive
        that is younger than specified date and time is used.

            $ emborg restore --date 2021-04-01 resume.doc
            $ emborg restore --date 2021-04-01T18:30 resume.doc

        Or you can specify the date in relative terms:

            $ emborg restore --date 3d  resume.doc

        In this case 3d means 3 days.  You can use s, m, h, d, w, M, and y to
        represent seconds, minutes, hours, days, weeks, months, and years.

        This command is very similar to the extract command except that it is
        meant to be replace files while in place.  The extract command is
        preferred if you would like to extract the files to a new location.
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "first"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        paths = cmdline["<path>"]
        archive = cmdline["--archive"]
        date = cmdline["--date"]
        borg_opts = []
        if cmdline["--list"]:
            borg_opts.append("--list")

        # convert given paths into the equivalent paths found in the archive
        paths = get_archive_paths(paths, settings)

        # get the desired archive
        if date and not archive:
            archive = get_name_of_nearest_archive(settings, date)
        if not archive:
            archive = get_name_of_latest_archive(settings)
        display("Archive:", archive)

        # run borg
        borg = settings.run_borg(
            cmd = "extract",
            borg_opts = borg_opts,
            args = [settings.destination(archive)] + paths,
            emborg_opts = options,
            show_borg_output = bool(borg_opts),
            use_working_dir = True,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# SettingsCommand command {{{1
class SettingsCommand(Command):
    NAMES = "settings setting".split()
    DESCRIPTION = "list settings of chosen configuration"
    USAGE = dedent(
        """
        Usage:
            emborg [options] settings [<name>]
            emborg [options] setting [<name>]

        Options:
            -a, --available   list available settings
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = False
    COMPOSITE_CONFIGS = "error"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        show_available = cmdline["--available"]
        width = 26
        leader = (width+2)*' '
        unknown = Color("yellow", Color.isTTY())
        known = Color("cyan", Color.isTTY())
        resolved = Color("magenta", Color.isTTY())
        color_adjust = len(known('x')) - 1

        if show_available:
            def show_setting(name, desc):
                desc = fill(desc, 74-width-2)
                text = indent(
                    f"{known(name):>{width + color_adjust}}: {desc}",
                    leader = leader,
                    first = -1
                )
                output(text)

            output("Emborg settings:")
            for name in sorted(EMBORG_SETTINGS):
                show_setting(name, EMBORG_SETTINGS[name])

            output()
            output("Borg settings:")
            for name in sorted(BORG_SETTINGS):
                attrs = BORG_SETTINGS[name]
                show_setting(name, attrs['desc'])

            return 0

        if settings:
            requested = cmdline['<name>']
            for k, v in sorted(settings):
                is_known = k in EMBORG_SETTINGS or k in BORG_SETTINGS
                key = known(k) if is_known else unknown(k)
                if requested and requested != k:
                    continue
                if k == "passphrase":
                    v = "<set>"
                output(f"{key:>{width + color_adjust}}: {render(v, level=7)}")
                try:
                    if is_str(v) and "{" in v and k not in settings.do_not_expand:
                        output(resolved(
                            f'{leader}{render(settings.resolve(v), level=6)}'
                        ))
                except Error:
                    pass

    run_early = run
    # --available is handled in run_early


# UmountCommand command {{{1
class UmountCommand(Command):
    NAMES = "umount unmount".split()
    DESCRIPTION = "un-mount a previously mounted repository or archive"
    USAGE = dedent(
        """
        Usage:
            emborg umount [<mount_point>]
            emborg unmount [<mount_point>]
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "first"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        mount_point = cmdline["<mount_point>"]
        if mount_point:
            mount_point = settings.to_path(mount_point, resolve=False)
        else:
            mount_point = settings.as_path("default_mount_point")
        if not mount_point:
            raise Error("must specify directory to use as mount point")

        # run borg
        try:
            settings.run_borg(
                cmd="umount", args=[mount_point], emborg_opts=options,
            )
            try:
                mount_point.rmdir()
            except OSError as e:
                warn(os_error(e))
        except Error as e:
            if "busy" in str(e):
                e.reraise(
                    codicil = f"Try running 'lsof +D {mount_point!s}' to find culprit."
                )


# VersionCommand {{{1
class VersionCommand(Command):
    NAMES = ("version",)
    DESCRIPTION = "display emborg version"
    USAGE = dedent(
        """
        Usage:
            emborg version
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = False
    COMPOSITE_CONFIGS = "none"

    @classmethod
    def run_early(cls, command, args, settings, options):

        # get the Python version
        python = "Python {}.{}.{}".format(
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        )

        # output the Emborg version along with the Python version
        from . import __version__, __released__

        output("emborg version: %s (%s) [%s]." % (__version__, __released__, python))

        # Need to quit now.  The version command need not have a valid settings
        # file, so if we keep going emborg might emit spurious errors if the
        # settings files are not yet properly configured.
        return 0
