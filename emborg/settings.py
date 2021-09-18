# Settings

# License {{{1
# Copyright (C) 2018-2021 Kenneth S. Kundert
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
import errno
import os
import re
from textwrap import dedent

import arrow

from inform import (
    Color,
    Error,
    LoggingCache,
    codicil,
    comment,
    conjoin,
    display,
    done,
    errors_accrued,
    full_stop,
    get_informer,
    indent,
    is_str,
    join,
    log,
    narrate,
    output,
    plural,
    render,
    warn,
)
from shlib import (
    Run, cd, cwd, getmod, mv, render_command, rm, to_path,
    set_prefs as set_shlib_prefs
)

from .collection import Collection, split_lines
from .hooks import Hooks
from .patterns import (
    check_excludes,
    check_excludes_files,
    check_patterns,
    check_patterns_files,
    check_roots,
)
from .preferences import (
    BORG,
    BORG_SETTINGS,
    CONFIG_DIR,
    CONFIGS_SETTING,
    DATA_DIR,
    DATE_FILE,
    DEFAULT_CONFIG_SETTING,
    DEFAULT_ENCODING,
    INCLUDE_SETTING,
    INITIAL_HOME_CONFIG_FILE_CONTENTS,
    INITIAL_ROOT_CONFIG_FILE_CONTENTS,
    INITIAL_SETTINGS_FILE_CONTENTS,
    LOCK_FILE,
    LOG_FILE,
    PREV_LOG_FILE,
    PROGRAM_NAME,
    SETTINGS_FILE,
    convert_name_to_option,
)
from .python import PythonFile
from .utilities import getfullhostname, gethostname, getusername

# Globals {{{1
borg_commands_with_dryrun = "create extract delete prune upgrade recreate".split()
set_shlib_prefs(use_inform=True, log_cmd=True, encoding=DEFAULT_ENCODING)

# Utilities {{{1
hostname = gethostname()
fullhostname = getfullhostname()
username = getusername()


# borg_options_arg_count {{{1
borg_options_arg_count = {
    "borg": 1,
    "--exclude": 1,
    "--exclude-from": 1,
    "--pattern": 1,
    "--patterns-from": 1,
    "--encryption": 1,
}
for name, attrs in BORG_SETTINGS.items():
    if "arg" in attrs and attrs["arg"]:
        borg_options_arg_count[convert_name_to_option(name)] = 1

# ConfigQueue {{{2
class ConfigQueue:
    def __init__(self, command=None):
        self.uninitialized = True
        if command:
            self.requires_exclusivity = command.REQUIRES_EXCLUSIVITY
            self.composite_config_response = command.COMPOSITE_CONFIGS
            self.show_config_name = command.SHOW_CONFIG_NAME
        else:
            # This is a result of an API call.
            # This will largely constrain use to scalar configs, if a composite
            # config is given, the only thing the user will be able to do is to
            # ask for the child configs.
            self.composite_config_response = None
            self.requires_exclusivity = True
            self.composite_config_response = 'restricted'
            self.show_config_name = False

    def initialize(self, name, settings):
        self.uninitialized = False
        all_configs = Collection(settings.get(CONFIGS_SETTING, ""))
        default = settings.get(DEFAULT_CONFIG_SETTING)

        # identify the available configurations and config groups
        config_groups = {}
        for config in all_configs:
            if "=" in config:
                group, _, sub_configs = config.partition("=")
                sub_configs = sub_configs.split(",")
            else:
                group = config
                sub_configs = [config]
            config_groups[group] = sub_configs

        # get the name of the desired configuration and assure it exists
        if not name:
            name = default
        if name:
            if name not in config_groups:
                raise Error(
                    "unknown configuration.",
                    culprit = name,
                    codicil = "Perhaps you forgot to add it to the 'configurations' setting?.",
                )
        else:
            if len(configs) > 0:
                name = configs[0]
            else:
                raise Error("no known configurations.", culprit=CONFIGS_SETTING)

        # set the config queue
        # convert configs to list while preserving order and eliminating dupes
        configs = list(dict.fromkeys(config_groups[name]))
        self.configs = configs[:]
        num_configs = len(configs)
        if num_configs > 1:
            if self.composite_config_response == "error":
                raise Error("command does not support composite configs.", culprit=name)
        elif num_configs < 1:
            raise Error("empty composite config.", culprit=name)

        if self.composite_config_response == "first":
            self.remaining_configs = configs[0:]
        elif self.composite_config_response == "none":
            self.remaining_configs = [None]
        else:
            self.remaining_configs = list(reversed(configs))

        # determine whether to display sub-config name
        if self.show_config_name:
            self.show_config_name = 'first'
            if len(self.remaining_configs) <= 1:
                self.show_config_name = False


    def get_active_config(self):
        active_config = self.remaining_configs.pop()
        if self.show_config_name:
            if self.show_config_name != 'first':
                display()
            display("===", active_config, "===")
            self.show_config_name = True
        return active_config

    def __bool__(self):
        return bool(self.uninitialized or self.remaining_configs)


# Settings class {{{1
class Settings:
    # Constructor {{{2
    def __init__(self, config=None, emborg_opts=(), _queue=None):
        self.settings = dict()
        self.do_not_expand = ()
        self.emborg_opts = emborg_opts

        # reset the logfile so anything logged after this is placed in the
        # logfile for this config
        get_informer().set_logfile(LoggingCache())
        self.config_dir = to_path(CONFIG_DIR)
        self.read_config(name=config, queue=_queue)
        self.check()
        set_shlib_prefs(encoding=self.encoding if self.encoding else DEFAULT_ENCODING)
        self.hooks = Hooks(self)

        # set colorscheme
        if self.colorscheme:
            colorscheme = self.colorscheme.lower()
            if colorscheme == 'none':
                get_informer().colorscheme = None
            elif colorscheme in ('light', 'dark'):
                get_informer().colorscheme = colorscheme
            else:
                warn(f'unknown colorscheme: {self.colorscheme}.')

    # read_config() {{{2
    def read_config(self, name=None, path=None, queue=None):
        """Recursively read configuration files.

        name (str):
            Name of desired configuration. Passed only when reading the top level
            settings file. Default is the default configuration as specified in the
            settings file, or if that is not specified then the first configuration
            given is used.
        path (str):
            Full path to settings file. Should not be given for the top level
            settings file (SETTINGS_FILE in CONFIG_DIR).
        """

        if path:
            # we are reading an include file
            settings = PythonFile(path).run()
            parent = path.parent
            includes = Collection(
                settings.get(INCLUDE_SETTING),
                split_lines,
                comment="#",
                strip=True,
                cull=True,
            )
        else:
            # this is the base-level settings file
            parent = self.config_dir
            if not parent.exists():
                # config dir does not exist, create and populate it
                narrate("creating config directory:", str(parent))
                parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                for name, contents in [
                    (SETTINGS_FILE, INITIAL_SETTINGS_FILE_CONTENTS),
                    ("root", INITIAL_ROOT_CONFIG_FILE_CONTENTS),
                    ("home", INITIAL_HOME_CONFIG_FILE_CONTENTS),
                ]:
                    path = parent / name
                    path.write_text(contents)
                    path.chmod(0o600)
                output(
                    f"Configuration directory created: {parent!s}.",
                    "Includes example settings files. Edit them to suit your needs.",
                    "Search for and replace any fields delimited with << and >>.",
                    "Delete any configurations you do not need.",
                    "Generally you will use either home or root, but not both.",
                    sep="\n",
                )
                done()

            # read the shared settings file
            path = PythonFile(parent, SETTINGS_FILE)
            self.settings_filename = path.path
            settings = path.run()

            # initialize the config queue
            if not queue:
                # this is a request through the API
                queue = ConfigQueue()
            if queue.uninitialized:
                queue.initialize(name, settings)
            config = queue.get_active_config()
            self.configs = queue.configs

            # save config name
            settings["config_name"] = config
            self.config_name = config
            if not config:
                # this happens on composite configs for commands that do not
                # need access to a specific config, such as help and configs
                self.settings.update(settings)
                return

            # get includes
            includes = Collection(settings.get(INCLUDE_SETTING))
            includes = [config] + list(includes.values())

        if settings.get("passphrase"):
            if getmod(path) & 0o077:
                warn("file permissions are too loose.", culprit=path)
                codicil(f"Recommend running: chmod 600 {path!s}")

        self.settings.update(settings)

        # read include files, if any are specified
        for include in includes:
            path = to_path(parent, include)
            self.read_config(path=path)

    # check() {{{2
    def check(self):
        # add some possibly useful placeholders into settings
        home_dir = os.environ.get("HOME")
        if home_dir and "home_dir" not in self.settings:
            self.settings["home_dir"] = home_dir
        self.settings["config_dir"] = CONFIG_DIR
        self.settings["log_dir"] = DATA_DIR
        self.do_not_expand = Collection(self.settings.get("do_not_expand", ""))

        # gather the string valued settings together (can be used by resolve)
        self.str_settings = {k: v for k, v in self.settings.items() if is_str(v)}

        if not self.config_name:
            # running a command that does not need settings, such as configs
            return

        # complain about required settings that are missing
        missing = []
        required_settings = "repository".split()
        for each in required_settings:
            if not self.settings.get(each):
                missing.append(each)
        if missing:
            m = conjoin(missing)
            raise Error(f"{m}: no value given for {plural(missing):setting}.")

        self.working_dir = to_path(self.settings.get("working_dir", "/"))
        if not self.working_dir.exists():
            raise Error("{self.working_dir!s} not found.", culprit="working_dir")
        if not self.working_dir.is_absolute():
            raise Error("must be an absolute path.", culprit="working_dir")

    # handle errors {{{2
    def fail(self, *msg, cmd='<unknown>'):
        msg = join(*msg)
        try:
            msg = msg.decode('ascii', errors='replace')
        except AttributeError:
            pass
        try:
            if self.notify and not Color.isTTY():
                Run(
                    ["mail", "-s", f"{PROGRAM_NAME} failed on {username}@{hostname}"]
                    + self.notify.split(),
                    stdin=dedent(
                        f"""\
                        {PROGRAM_NAME} fails.

                        command: {cmd}
                        config: {self.config_name}
                        source: {username}@{fullhostname}:{', '.join(str(d) for d in self.src_dirs)}
                        destination: {self.repository!s}
                        error message:
                        """
                    ) + indent(msg) + "\n",
                    modes="soeW",
                    encoding="ascii",
                )
        except Error:
            pass
        try:
            notifier = self.settings.get("notifier")
            # don't use self.value as we don't want arguments expanded yet
            if notifier and not Color.isTTY():
                Run(
                    self.notifier.format(
                        cmd=cmd,
                        msg=msg,
                        hostname=hostname,
                        user_name=username,
                        prog_name=PROGRAM_NAME,
                    ),
                    modes="SoeW"
                    # need to use the shell as user will generally quote msg
                )
        except Error:
            pass
        except KeyError as e:
            warn("unknown key.", culprit=(self.settings_file, "notifier", e))

    # get value {{{2
    def value(self, name, default=""):
        """Gets value of scalar setting."""
        value = self.settings.get(name, default)
        if not is_str(value) or name in self.do_not_expand:
            return value
        return self.resolve(value)

    # get values {{{2
    def values(self, name, default=()):
        """Gets value of list setting."""
        values = Collection(
            self.settings.get(name, default),
            split_lines,
            comment="#",
            strip=True,
            cull=True,
        )
        if name in self.do_not_expand:
            return values
        return [self.resolve(v) for v in values]

    # resolve {{{2
    def resolve(self, value):
        """Expand any embedded names in value"""

        # escape any double braces
        try:
            value = value.replace("{{", r"\b").replace("}}", r"\e")
        except AttributeError:
            if isinstance(value, int) and not isinstance(value, bool):
                return str(value)
            return value

        # expand names contained in braces
        try:
            resolved = value.format(
                host_name=hostname,
                user_name=username,
                prog_name=PROGRAM_NAME,
                **self.str_settings,
            )
        except KeyError as e:
            raise Error("unknown setting.", culprit=e)
        if resolved != value:
            resolved = self.resolve(resolved)

        # restore escaped double braces with single braces
        return resolved.replace(r"\b", "{").replace(r"\e", "}")

    # to_path() {{{2
    def to_path(self, s, resolve=True, culprit=None):
        """Converts a string to a path."""
        p = to_path(s)
        if resolve:
            p = to_path(self.working_dir, p)
        if culprit:
            if not p.exists():
                raise Error(f"{p!s} not found.", culprit=culprit)
        return p

    # as_path() {{{2
    def as_path(self, name, resolve=True, must_exist=False, default=None):
        """Converts a setting to a path, without resolution."""
        s = self.value(name, default)
        if s:
            return self.to_path(s, resolve, name if must_exist else None)

    # resolve_patterns() {{{2
    def resolve_patterns(self, borg_opts, skip_checks=False):
        roots = self.src_dirs[:]

        patterns = self.values("patterns")
        if patterns:
            for pattern in check_patterns(
                patterns, roots, self.working_dir, "patterns",
                skip_checks=skip_checks
            ):
                borg_opts.extend(["--pattern", pattern])

        excludes = self.values("excludes")
        if excludes:
            for exclude in check_excludes(excludes, roots, "excludes"):
                borg_opts.extend(["--exclude", exclude])

        patterns_froms = self.as_paths("patterns_from", must_exist=True)
        if patterns_froms:
            check_patterns_files(
                patterns_froms, roots, self.working_dir, skip_checks=skip_checks
            )
            for patterns_from in patterns_froms:
                borg_opts.extend(["--patterns-from", patterns_from])

        exclude_froms = self.as_paths("exclude_from", must_exist=True)
        if exclude_froms:
            check_excludes_files(exclude_froms, roots)
            for exclude_from in exclude_froms:
                borg_opts.extend(["--exclude-from", exclude_from])

        if not skip_checks:
            check_roots(roots, self.working_dir)

        if errors_accrued():
            raise Error("stopping due to previously reported errors.")
        self.roots = roots

    # as_paths() {{{2
    def as_paths(self, name, resolve=True, must_exist=False):
        """Convert setting to paths, without resolution."""
        return [
            self.to_path(s, resolve, name if must_exist else None)
            for s in self.values(name)
        ]

    # borg_options() {{{2
    def borg_options(self, cmd, borg_opts, emborg_opts, strip_prefix):
        if not borg_opts:
            borg_opts = []

        # handle special cases first {{{3
        if self.value("verbose"):
            emborg_opts = list(emborg_opts)
            emborg_opts.append("verbose")
        if "verbose" in emborg_opts:
            borg_opts.append("--verbose")
        if "dry-run" in emborg_opts and cmd in borg_commands_with_dryrun:
            borg_opts.append("--dry-run")

        if cmd == "create":
            if "verbose" in emborg_opts and "--list" not in borg_opts:
                borg_opts.append("--list")
            self.resolve_patterns(borg_opts)

        elif cmd == "extract":
            if "verbose" in emborg_opts:
                borg_opts.append("--list")

        elif cmd == "init":
            if self.passphrase or self.passcommand or self.avendesora_account:
                encryption = self.encryption if self.encryption else "repokey"
                borg_opts.append(f"--encryption={encryption}")
                if encryption == "none":
                    warn("passphrase given but not needed as encryption set to none.")
                if encryption.startswith("keyfile"):
                    warn(
                        dedent(
                            """
                            you should use 'borg key export' to export the
                            encryption key, and then keep that key in a safe
                            place.  You can do this with emborg using 'emborg
                            borg key export @repo <outfile>'.  If you lose the
                            key you will lose access to, your backups.
                            """
                        ).strip(),
                        wrap=True,
                    )
            else:
                encryption = self.encryption if self.encryption else "none"
                if encryption != "none":
                    raise Error("passphrase not specified.")
                borg_opts.append(f"--encryption={encryption}")

        if (
            cmd in ["create", "delete", "prune"]
            and "dry-run" not in emborg_opts
            and not ("--list" in borg_opts or "--progress" in borg_opts)
        ):
            # By default we ask for stats to go in the log file.  However if
            # opts contains --list, then the stats will be displayed to user
            # rather than going to logfile, in this case, do not request stats
            # automatically, require user to do it manually.
            borg_opts.append("--stats")

        # add the borg command line options appropriate to this command {{{3
        for name, attrs in BORG_SETTINGS.items():
            if strip_prefix and name == "prefix":
                continue
            if cmd in attrs["cmds"] or "all" in attrs["cmds"]:
                opt = convert_name_to_option(name)
                val = self.value(name)
                if val:
                    if "arg" in attrs and attrs["arg"]:
                        borg_opts.extend([opt, str(val)])
                    else:
                        borg_opts.extend([opt])
        return borg_opts

    # publish_passcode() {{{2
    def publish_passcode(self):
        for v in ['BORG_PASSPHRASE', 'BORG_PASSCOMMAND', 'BORG_PASSPHRASE_FD']:
            if v in os.environ:
                narrate(f"Using existing {v}.")
                return

        passcommand = self.value('passcommand')
        passcode = self.passphrase

        # process passcomand
        if passcommand:
            if passcode:
                warn("passphrase unneeded.", culprit="passcommand")
            narrate(f"Setting BORG_PASSCOMMAND.")
            os.environ['BORG_PASSCOMMAND'] = passcommand
            self.borg_passcode_env_var_set_by_emborg = 'BORG_PASSCOMMAND'
            return

        # get passphrase from avendesora
        if not passcode and self.avendesora_account:
            narrate("running avendesora to access passphrase.")
            try:
                from avendesora import PasswordGenerator

                pw = PasswordGenerator()
                account_spec = self.value("avendesora_account")
                if ':' in account_spec:
                    passcode = str(pw.get_value(account_spec))
                else:
                    account = pw.get_account(self.value("avendesora_account"))
                    field = self.value("avendesora_field", None)
                    passcode = str(account.get_value(field))
            except ImportError:
                raise Error(
                    "Avendesora is not available",
                    "you must specify passphrase in settings.",
                    sep=", ",
                )

        if passcode:
            os.environ['BORG_PASSPHRASE'] = passcode
            narrate(f"Setting BORG_PASSPHRASE.")
            self.borg_passcode_env_var_set_by_emborg = 'BORG_PASSPHRASE'
            return

        if self.encryption is None:
            self.encryption = "none"
        if self.encryption == "none" or self.encryption.startswith('authenticated'):
            comment("Encryption is disabled.")
            return
        raise Error("Cannot determine the encryption passphrase.")

    # run_borg() {{{2
    def run_borg(
        self,
        cmd,
        args=(),
        borg_opts=None,
        emborg_opts=(),
        strip_prefix=False,
        show_borg_output=False,
        use_working_dir=False,
    ):
        # prepare the command
        self.publish_passcode()
        if "BORG_PASSPHRASE" in os.environ:
            os.environ["BORG_DISPLAY_PASSPHRASE"] = "no"
        if self.ssh_command:
            os.environ["BORG_RSH"] = self.ssh_command
        environ = {k: v for k, v in os.environ.items() if k.startswith("BORG_")}
        if "BORG_PASSPHRASE" in environ:
            environ["BORG_PASSPHRASE"] = "<redacted>"
        executable = self.value("borg_executable", BORG)
        borg_opts = self.borg_options(cmd, borg_opts, emborg_opts, strip_prefix)
        command = [executable] + cmd.split() + borg_opts + args
        narrate("Borg-related environment variables:", render(environ))

        # check if ssh agent is present
        if self.needs_ssh_agent:
            if "SSH_AUTH_SOCK" not in os.environ:
                warn(
                    "SSH_AUTH_SOCK environment variable not found.",
                    "Is ssh-agent running?",
                )

        # run the command
        narrate(
            "running:\n{}".format(
                indent(render_command(command, borg_options_arg_count))
            )
        )
        with cd(self.working_dir if use_working_dir else "."):
            narrate("running in:", cwd())
            if "--json" in command or "--json-lines" in command:
                narrating = False
            else:
                narrating = (
                    show_borg_output
                    or "--verbose" in borg_opts
                    or "--progress" in borg_opts
                    or "verbose" in emborg_opts
                    or "narrate" in emborg_opts
                )
            if narrating:
                modes = "soeW"
                display("\nRunning Borg {} command ...".format(cmd))
            else:
                modes = "sOEW"
            starts_at = arrow.now()
            log("starts at: {!s}".format(starts_at))
            try:
                borg = Run(command, modes=modes, stdin="", env=os.environ, log=False)
            except Error as e:
                self.report_borg_error(e, cmd)
            finally:
                # remove passcode env variables created by emborg
                if self.borg_passcode_env_var_set_by_emborg:
                    narrate(f"Unsetting {self.borg_passcode_env_var_set_by_emborg}.")
                    del os.environ[self.borg_passcode_env_var_set_by_emborg]
            ends_at = arrow.now()
            log("ends at: {!s}".format(ends_at))
            log("elapsed = {!s}".format(ends_at - starts_at))
        if borg.stdout:
            narrate("Borg stdout:")
            narrate(indent(borg.stdout))
        if borg.stderr:
            narrate("Borg stderr:")
            narrate(indent(borg.stderr))
        if borg.status:
            narrate("Borg exit status:", borg.status)
        return borg

    # run_borg_raw() {{{2
    def run_borg_raw(self, args):

        # prepare the command
        self.publish_passcode()
        os.environ["BORG_DISPLAY_PASSPHRASE"] = "no"
        executable = self.value("borg_executable", BORG)
        remote_path = self.value("remote_path")
        remote_path = ["--remote-path", remote_path] if remote_path else []
        repository = str(self.repository)
        command = (
            [executable]
            + remote_path
            + [a.replace('@repo', repository) for a in args]
        )

        # run the command
        narrate(
            "running:\n{}".format(
                indent(render_command(command, borg_options_arg_count))
            )
        )
        with cd(self.working_dir):
            narrate("running in:", cwd())
            starts_at = arrow.now()
            log("starts at: {!s}".format(starts_at))
            try:
                borg = Run(command, modes="soeW", env=os.environ, log=False)
            except Error as e:
                self.report_borg_error(e, ' '.join(command))
            ends_at = arrow.now()
            log("ends at: {!s}".format(ends_at))
            log("elapsed = {!s}".format(ends_at - starts_at))
        if borg.stdout:
            narrate("Borg stdout:")
            narrate(indent(borg.stdout))
        if borg.stderr:
            narrate("Borg stderr:")
            narrate(indent(borg.stderr))
        if borg.status:
            narrate("Borg exit status:", borg.status)

        return borg

    # report_borg_error() {{{2
    def report_borg_error(self, e, cmd):
        narrate('Borg terminates with exit status:', e.status)
        codicil = None
        if e.stderr:
            if 'previously located at' in e.stderr:
                codicil = dedent(f'''
                    If repository was intentionally relocated, re-run with --relocated:
                        emborg --relocated {cmd} ...
                ''')
            if 'Failed to create/acquire the lock' in e.stderr:
                codicil = [
                    'If another Emborg or Borg process is using this repository,',
                    'please wait for it to finish.',
                    'Perhaps you still have an archive mounted?',
                    'If so, use ‘emborg umount’ to unmount it.',
                    'Perhaps a previous run was killed or terminated with an error?',
                    'If so, use ‘emborg breaklock’ to clear the lock.',
                ]

            if 'Mountpoint must be a writable directory' in e.stderr:
                codicil = 'Perhaps an archive is already mounted there?'
        e.reraise(culprit=f"borg {cmd}", codicil=codicil)

    # destination() {{{2
    def destination(self, archive=None):
        if archive is True:
            archive = self.value("archive")
            if not archive:
                raise Error("setting value not available.", culprit="archive")
        if archive:
            return f"{self.repository!s}::{archive}"
        return self.repository

    # is_config() {{{2
    def is_first_config(self):
        return self.config_name == self.configs[0]

    def is_last_config(self):
        return self.config_name == self.configs[-1]

    # get attribute {{{2
    def __getattr__(self, name):
        return self.settings.get(name)

    # iterate through settings {{{2
    def __iter__(self):
        for key in sorted(self.settings.keys()):
            yield key, self.settings[key]

    # enter {{{2
    def __enter__(self):
        if not self.config_name:
            # this command does not require config
            return self

        self.borg_passcode_env_var_set_by_emborg = None

        # resolve src directories
        self.src_dirs = self.as_paths("src_dirs", resolve=False)

        # set repository
        repository = self.value("repository")
        if ":" not in repository:
            # is a local repository
            repository = to_path(repository)
            if not repository.is_absolute():
                raise Error(
                    "local repository must be specified using an absolute path.",
                    culprit=repository,
                )
        self.repository = repository

        # default archive if not given
        if "archive" not in self.settings:
            if "prefix" not in self.settings:
                self.settings["prefix"] = "{host_name}-{user_name}-{config_name}-"
            self.settings["archive"] = self.prefix + "{{now}}"

        # assure that prefix does not contain {{now}}
        if "prefix" in self.settings:
            match = re.search(
                r'{{\s*((?:utc)?now)\s*[:}]',
                self.settings["prefix"],
                re.I
            )
            if match:
                bad_key = '{{' + match.group(1) + '}}'
                raise Error(f'prefix setting must not contain {bad_key}.')

        # resolve other files and directories
        data_dir = to_path(DATA_DIR)
        if not data_dir.exists():
            # data dir does not exist, create it
            data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.date_file = data_dir / self.resolve(DATE_FILE)
        self.data_dir = data_dir

        # perform locking
        lockfile = self.lockfile = data_dir / self.resolve(LOCK_FILE)
        if self.requires_exclusivity:
            # check for existence of lockfile
            if lockfile.exists():
                report = True
                try:
                    lock_contents = lockfile.read_text()
                    pid = None
                    for l in lock_contents.splitlines():
                        name, _, value = l.partition("=")
                        if name.strip().lower() == "pid":
                            pid = int(value.strip())
                    assert pid > 0
                    os.kill(pid, 0)
                except ProcessLookupError as e:
                    if e.errno == errno.ESRCH:
                        report = False  # process no longer exists
                except Exception as e:
                    log("garbled lock file:", e)

                if report:
                    raise Error(f"currently running (see {lockfile} for details).")

            # create lockfile
            now = arrow.now()
            pid = os.getpid()
            lockfile.write_text(
                dedent(
                    f"""
                    started = {now!s}
                    pid = {pid}
                    """
                ).lstrip()
            )

        # open logfile
        # do this after checking lock so we do not overwrite logfile
        # of emborg process that is currently running
        self.logfile = data_dir / self.resolve(LOG_FILE)
        if "no-log" not in self.emborg_opts:
            self.prev_logfile = data_dir / self.resolve(PREV_LOG_FILE)
            rm(self.prev_logfile)
            if self.logfile.exists():
                mv(self.logfile, self.prev_logfile)
            get_informer().set_logfile(self.logfile)

        log("working dir =", self.working_dir)
        return self

    # exit {{{2
    def __exit__(self, exc_type, exc_val, exc_tb):

        # delete lockfile
        if self.requires_exclusivity:
            self.lockfile.unlink()
