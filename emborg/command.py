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
from textwrap import dedent

import arrow
from docopt import docopt

from inform import (
    Color,
    Error,
    comment,
    conjoin,
    display,
    full_stop,
    is_str,
    narrate,
    os_error,
    output,
    render,
    warn,
)
from shlib import Run, cwd, mkdir, rm, set_prefs, to_path

from .collection import Collection
from .preferences import BORG_SETTINGS, DEFAULT_COMMAND, EMBORG_SETTINGS, PROGRAM_NAME
from .utilities import gethostname, two_columns

# Utilities {{{1
hostname = gethostname()
set_prefs(use_inform=True, log_cmd=True)


# title() {{{2
def title(text):
    return full_stop(text.capitalize())


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
        date = arrow.get(date)
    except arrow.parser.ParserError:
        raise Error("invalid date specification.", culprit=date)
    for archive in archives:
        if arrow.get(archive["time"]) >= date:
            return archive["name"]
    raise Error("archive not available.", culprit=date)


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

# require_env_variable() {{{2
def require_env_var(var, feature, command, args):
    val = os.environ.get(var)
    if val != 'YES':
        cmd = f"emborg {command} {' '.join(args)}"
        raise Error(
            f"environment variable must be set to YES to use {' '.join(feature)}.",
            culprit=var,
            codicil=f"TO use, try:\n    {var}=YES {cmd}",
        )

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
        # settings files have been read. As such, the settings argument is None.
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
        # configurations have been run. As such, the settings argument is None.
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

        Breaks both the local and the repository locks. Be sure Borg is no longer
        running before using this command.
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
            require_env_var(
                'BORG_CHECK_I_KNOW_WHAT_I_AM_DOING', repair, command, args
            )

        # identify archive or archives to check
        if check_all:
            archive = None
        elif not archive:
            archive = get_name_of_latest_archive(settings)

        # run borg
        borg = settings.run_borg(
            cmd="check",
            args=verify + repair + [settings.destination(archive)],
            emborg_opts=options,
            strip_prefix=include_external_archives,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


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
            -f, --fast    skip pruning and checking for a faster backup on a slow network
            -l, --list    list the files and directories as they are processed
            -s, --stats   show Borg statistics

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

        # check the dependencies are available
        must_exist = settings.as_paths("must_exist")
        for path in must_exist:
            if not path.exists():
                raise Error(
                    "does not exist, perform setup and restart.",
                    culprit=("must_exist", path),
                )

        # run prerequisites
        cmds = settings.values("run_before_backup")
        for cmd in cmds:
            narrate("running pre-backup script:", cmd)
            try:
                Run(cmd, "SoEW")
            except Error as e:
                e.reraise(culprit=("run_before_backup", cmd.split()[0]))

        # run borg
        src_dirs = settings.src_dirs
        try:
            settings.run_borg(
                cmd="create",
                borg_opts=borg_opts,
                args=[settings.destination(True)] + src_dirs,
                emborg_opts=options,
                show_borg_output=bool(borg_opts),
                use_working_dir=True,
            )
        except Error as e:
            if e.stderr and "is not a valid repository" in e.stderr:
                e.reraise(codicil="Run 'emborg init' to initialize the repository.")
            else:
                raise

        # update the date files
        narrate("update date file")
        now = arrow.now()
        settings.date_file.write_text(str(now))

        # run any scripts specified to be run after a backup
        cmds = settings.values("run_after_backup")
        for cmd in cmds:
            narrate("running post-backup script:", cmd)
            try:
                Run(cmd, "SoEW")
            except Error as e:
                e.reraise(culprit=("run_after_backup", cmd.split()[0]))

        if cmdline["--fast"]:
            return

        # check and prune the archives if requested
        try:
            # check the archives if requested
            activity = "checking"
            if settings.check_after_create:
                narrate("checking archive")
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
                        cuplrit="check_after_create",
                    )
                    args = []
                check = CheckCommand()
                check.run("check", args, settings, options)

            activity = "pruning"
            if settings.prune_after_create:
                narrate("pruning archives")
                prune = PruneCommand()
                args = ["--stats"] if cmdline["--stats"] else []
                prune.run("prune", args, settings, options)
        except Error as e:
            e.reraise(
                codicil=(
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
            -l, --latest   delete the most recently created archive
            -s, --stats    show Borg statistics
        """
    ).strip()
    # borg allows you to delete all archives by simply not specifying an
    # archive, but then it interactively asks the user to type YES if that
    # deletes all archives from repository. Emborg currently does not have
    # the ability support this and there appears to be no way of stopping
    # borg from asking for confirmation, so just limit user to deleting one
    # archive at a time.
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "error"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        archive = cmdline["<archive>"]
        if not archive:
            archive = get_name_of_latest_archive(settings)
        if not archive:
            raise Error("archive missing.")
        show_stats = cmdline["--stats"] or settings.show_stats

        # run borg
        borg = settings.run_borg(
            cmd="delete",
            args=[settings.destination(archive)],
            emborg_opts=options,
            strip_prefix=True,
            show_borg_output=show_stats,
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
            emborg diff <archive1> <archive2>
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

        # run borg
        borg = settings.run_borg(
            cmd="diff",
            args=[settings.destination(archive1), archive2],
            emborg_opts=options,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


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
                        culprit=e.args[0],
                        codicil=cmdline["--message"],
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
                stdin=message,
                modes="soeW",
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

            emborg extract home/ken/src/verif/av/manpages/settings.py

        Use manifest to determine what path you should specify to identify the
        desired file or directory (they will paths relative to the working
        directory, which defaults to / but can be overridden in a configuration
        file).  The paths may point to directories, in which case the entire
        directory is extracted. It may also be a glob pattern.

        If you do not specify an archive or date, the most recent archive is
        used.  You can extract the version of a file or directory that existed
        on a particular date using:

            emborg extract --date 2015-04-01 home/ken/src/verif/av/manpages/settings.py

        Or, you can extract the version from a particular archive using:

            emborg extract --archive kundert-2018-12-05T12:54:26 home/ken/src/verif/av/manpages/settings.py

        The extracted files are placed in the current working directory with
        the original hierarchy. Thus, the above commands create the file:

            ./home/ken/src/verif/av/manpages/settings.py

        Normally, extract refuses to run if your current directory is the
        working directory used by Emborg so as to avoid overwriting an existing
        file.  If your intent is to overwrite the existing file, you can specify
        the --force option. Or, consider using the restore command; it
        overwrites the existing file regardless of what directory you run from.
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
                    wrap=True,
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
        output("Archive:", archive)

        # run borg
        borg = settings.run_borg(
            cmd="extract",
            borg_opts=borg_opts,
            args=[settings.destination(archive)] + paths,
            emborg_opts=options,
            show_borg_output=bool(borg_opts),
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

        # report local information
        src_dirs = (str(d) for d in settings.src_dirs)
        output(f"              config: {settings.config_name}")
        output(f'              source: {", ".join(src_dirs)}')
        output(f"         destination: {settings.destination()}")
        output(f"  settings directory: {settings.config_dir}")
        output(f"              logile: {settings.logfile}")
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
            cmd="info",
            args=[settings.destination()],
            emborg_opts=options,
            strip_prefix=True,
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
            cmd="list",
            args=["--short", settings.destination()],
            emborg_opts=options,
            strip_prefix=include_external_archives,
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
            emborg [options] manifest
            emborg [options] m
            emborg [options] la
            emborg [options] files
            emborg [options] f

        Options:
            -a <archive>, --archive <archive>   name of the archive to use
            -d <date>, --date <date>            date of the desired archive
            -l, --long                          use long listing format
            -f, --full                          use full listing format
            -n, --name-only                     use name only listing format
            -N, --sort-by-name                  sort by filename
            -D, --sort-by-date                  sort by date
            -S, --sort-by-size                  sort by size
            -O, --sort-by-owner                 sort by owner
            -G, --sort-by-group                 sort by group
            -r, --reverse-sort                  reverse the sort order

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

        There are a variety of ways that you use to sort the output. For example,
        sort by size, use:

            emborg manifest -S
        """
    ).strip()
    REQUIRES_EXCLUSIVITY = True
    COMPOSITE_CONFIGS = "first"

    @classmethod
    def run(cls, command, args, settings, options):
        # read command line
        cmdline = docopt(cls.USAGE, argv=[command] + args)
        archive = cmdline["--archive"]
        date = cmdline["--date"]

        # get the desired archive
        if date and not archive:
            archive = get_name_of_nearest_archive(settings, date)
        if not archive:
            archive = get_name_of_latest_archive(settings)
        output("Archive:", archive)

        # run borg
        borg = settings.run_borg(
            cmd="list", args=[settings.destination(archive)], emborg_opts=options,
        )
        out = borg.stdout

        # define available formats
        formats = dict(
            name="{path}",
            date="{day} {date} {time} {path}",
            size="{Size:<5.2r} {path}",
            owner="{owner:<8} {path}",
            group="{group:<8} {path}",
            long="{Size:<5.2r} {date} {time} {path}",
            full="{permissions:<10} {owner:<6} {group:<6} {size:>8} {Date:YYMMDD HH:mm} {path}",
        )
        user_formats = settings.manifest_formats
        if user_formats:
            unknown = user_formats.keys() - formats.keys()
            if unknown:
                warn("unknown formats:", ", ".join(unknown), culprit="manifest_formats")
            formats.update(user_formats)

        # process sort options
        if cmdline["--sort-by-name"]:
            fmt = "name"

            def get_key(columns):
                return columns[7]

        elif cmdline["--sort-by-date"]:
            fmt = "date"

            def get_key(columns):
                date_time = " ".join(columns[5:7])
                return arrow.get(date_time, "YYYY-MM-DD HH:mm:ss")

        elif cmdline["--sort-by-size"]:
            fmt = "size"

            def get_key(columns):
                return int(columns[3])

        elif cmdline["--sort-by-owner"]:
            fmt = "owner"

            def get_key(columns):
                return columns[1]

        elif cmdline["--sort-by-group"]:
            fmt = "group"

            def get_key(columns):
                return columns[2]

        else:
            fmt = None
            get_key = None

        # process format options
        if cmdline["--name-only"]:
            fmt = "name"
        elif cmdline["--long"]:
            fmt = "long"
        elif cmdline["--full"]:
            fmt = "full"

        # sort the output
        lines = [l.split(maxsplit=7) for l in out.rstrip().splitlines()]
        if get_key:
            lines = sorted(lines, key=get_key)
        if cmdline["--reverse-sort"]:
            lines.reverse()

        # echo borg output if no formatting is necessary
        if not fmt:
            output(out)
            return

        # import QuantiPhy
        try:
            from quantiphy import Quantity

            Quantity.set_prefs(spacer="")
        except ImportError:
            comment("Could not import QuantiPhy.")

            def Quantity(value, units):
                return value

        # generate formatted output
        for columns in lines:
            output(
                formats[fmt].format(
                    permissions=columns[0],
                    owner=columns[1],
                    group=columns[2],
                    size=columns[3],
                    Size=Quantity(columns[3], "B"),
                    Date=arrow.get(" ".join(columns[5:7]), "YYYY-MM-DD HH:mm:ss"),
                    day=columns[4].rstrip(","),
                    date=columns[5],
                    time=columns[6],
                    path=columns[7],
                ),
                sep="\n",
            )


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
        current directory, it must be a directory. If it does not exist, it is
        created.

        If you do not specify an archive or date, the most recently created
        archive is mounted.

        You can mount an archive that existed on a particular date using:

            emborg mount --date 2015-04-01 backups

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
            cmd="mount",
            args=[settings.destination(archive), mount_point],
            emborg_opts=options,
            strip_prefix=include_external_archives,
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
        show_stats = cmdline["--stats"] or settings.show_stats

        # checking the settings
        intervals = "within last minutely hourly daily weekly monthly yearly"
        prune_settings = [("keep_" + s) for s in intervals.split()]
        if not any(settings.value(s) for s in prune_settings):
            prune_settings = conjoin(prune_settings, ", or ")
            raise Error(
                "No prune settings available",
                codicil=f"At least one of {prune_settings} must be specified.",
            )

        # run borg
        borg = settings.run_borg(
            cmd="prune",
            args=[settings.destination()],
            emborg_opts=options,
            strip_prefix=include_external_archives,
            show_borg_output=show_stats,
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

        This command is very similar to the extract command except that it is
        meant to be replace files while in place.
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

        # convert to paths relative to the working directory
        try:
            paths = [
                to_path(p).resolve().relative_to(settings.working_dir) for p in paths
            ]
        except ValueError as e:
            raise Error(e)

        # get the desired archive
        if date and not archive:
            archive = get_name_of_nearest_archive(settings, date)
        if not archive:
            archive = get_name_of_latest_archive(settings)
        output("Archive:", archive)

        # run borg
        borg = settings.run_borg(
            cmd="extract",
            borg_opts=borg_opts,
            args=[settings.destination(archive)] + paths,
            emborg_opts=options,
            show_borg_output=bool(borg_opts),
            use_working_dir=True,
        )
        out = borg.stdout
        if out:
            output(out.rstrip())


# SettingsCommand command {{{1
class SettingsCommand(Command):
    NAMES = "settings".split()
    DESCRIPTION = "list settings of chosen configuration"
    USAGE = dedent(
        """
        Usage:
            emborg [options] settings

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
        unknown = Color("yellow")
        known = Color("cyan")

        if show_available:
            output("Emborg settings:")
            for name, desc in EMBORG_SETTINGS.items():
                output(f"{known(name):>33s}: {desc}")

            output()
            output("Borg settings:")
            for name, attrs in BORG_SETTINGS.items():
                output(f"{known(name):>33s}: {attrs['desc']}")
            return 0

        if settings:
            for k, v in settings:
                is_known = k in EMBORG_SETTINGS or k in BORG_SETTINGS
                key = known(k) if is_known else unknown(k)
                if k == "passphrase":
                    v = "<set>"
                output(f"{key:>33}: {render(v, level=6)}")
                try:
                    if is_str(v) and "{" in v:
                        output(f'{"":>24}{render(settings.resolve(v), level=6)}')
                except Error:
                    pass

    run_early = run
    # --avalable is handled in run_early


# UmountCommand command {{{1
class UmountCommand(Command):
    NAMES = "umount unmount".split()
    DESCRIPTION = "un-mount a previously mounted repository or archive"
    USAGE = dedent(
        """
        Usage:
            emborg [options] umount [<mount_point>]
            emborg [options] unmount [<mount_point>]
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
                    codicil=f"Try running 'lsof +D {mount_point!s}' to find culprit."
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
        python = "Python %s.%s.%s" % (
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        )

        # output the Emborg version along with the Python version
        from . import __version__, __released__

        output("emborg version: %s (%s) [%s]." % (__version__, __released__, python))

        # Need to quit now. The version command need not have a valid settings
        # file, so if we keep going emborg might emit spurious errors if the
        # settings files are not yet properly configured.
        return 0
