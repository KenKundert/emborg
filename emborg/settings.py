# Settings

# License {{{1
# Copyright (C) 2018-2019 Kenneth S. Kundert
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
# along with this program.  If not, see http://www.gnu.org/licenses/.

# Imports {{{1
from .collection import Collection
from .preferences import (
    BORG,
    BORG_SETTINGS,
    CONFIG_DIR,
    DATA_DIR,
    CONFIGS_SETTING,
    convert_name_to_option,
    DATE_FILE,
    DEFAULT_CONFIG_SETTING,
    INCLUDE_SETTING,
    INITIAL_SETTINGS_FILE_CONTENTS,
    INITIAL_ROOT_CONFIG_FILE_CONTENTS,
    INITIAL_HOME_CONFIG_FILE_CONTENTS,
    LOCK_FILE,
    LOG_FILE,
    PREV_LOG_FILE,
    PROGRAM_NAME,
    SETTINGS_FILE,
)
from .python import PythonFile
from .utilities import gethostname, getusername, render_paths
from shlib import getmod, mv, rm, Run, to_path, render_command, to_path
from inform import (
    Color, Error, codicil, conjoin, display, done, full_stop, get_informer, 
    indent, is_str, narrate, output, render, warn,
)
from textwrap import dedent
import arrow
import os


# Utilities {{{1
hostname = gethostname()
username = getusername()

borg_commands_with_dryrun = 'create extract delete prune upgrade recreate'

# borg_options_arg_count {{{2
borg_options_arg_count = {
    'borg': 1,
    '--exclude': 1,
    '--exclude-from': 1,
    '--encryption': 1,
}
for name, attrs in BORG_SETTINGS.items():
    if 'arg' in attrs and attrs['arg']:
        borg_options_arg_count[convert_name_to_option(name)] = 1

# get_config {{{2
config_queue = None

class NoMoreConfigs(Exception):
    pass

def get_config(name, settings, composite_config_allowed, show_config_name):
    global config_queue

    if config_queue is not None:
        try:
            active_config = config_queue.pop(0)
            if show_config_name:
                display('\n===', active_config, '===')
            return active_config
        except IndexError:
            raise NoMoreConfigs()

    configs = Collection(settings.get(CONFIGS_SETTING, ''))
    default = settings.get(DEFAULT_CONFIG_SETTING)

    config_groups = {}
    for config in configs:
        if '=' in config:
            group, _, sub_configs = config.partition('=')
            sub_configs = sub_configs.split(',')
        else:
            group = config
            sub_configs = [config]
        config_groups[group] = sub_configs

    if not name:
        name = default
    if name:
        if name not in config_groups:
            raise Error('unknown configuration.', culprit=name)
    else:
        if len(configs) > 1:
            name = configs[0]
        else:
            raise Error(
                'no known configurations.',
                culprit=(settings_filename, CONFIGS_SETTING)
            )
    configs = list(config_groups[name])
    num_configs = len(configs)
    if num_configs > 1 and composite_config_allowed is False:
        raise Error('command does not support composite configs.', culprit=name)
    elif num_configs < 1:
        raise Error('empty composite config.', culprit=name)
    active_config = configs.pop(0)
    if composite_config_allowed is None:
        config_queue = []
    else:
        config_queue = configs
    if config_queue and show_config_name:
        display('===', active_config, '===')
    return active_config


# Settings class {{{1
class Settings:
    # Constructor {{{2
    def __init__(self, name=None, command=None, options=()):
        if command:
            self.requires_exclusivity = command.REQUIRES_EXCLUSIVITY
            self.composite_config_allowed = command.COMPOSITE_CONFIGS
            self.show_config_name = command.SHOW_CONFIG_NAME
        else:
            self.requires_exclusivity = True
            self.composite_config_allowed = False
            self.show_config_name = False
        self.settings = {}
        self.options = options
        self.config_dir = to_path(CONFIG_DIR)
        self.read(name)
        self.check()

    # read() {{{2
    def read(self, name=None, path=None):
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
            settings = PythonFile(path).run()
            parent = path.parent
            includes = Collection(settings.get(INCLUDE_SETTING))
        else:
            # this is the generic settings file
            parent = self.config_dir
            if not parent.exists():
                # config dir does not exist, create and populate it
                narrate('creating config directory:', str(parent))
                parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                for name, contents in [
                    (SETTINGS_FILE, INITIAL_SETTINGS_FILE_CONTENTS),
                    ('root', INITIAL_ROOT_CONFIG_FILE_CONTENTS),
                    ('home', INITIAL_HOME_CONFIG_FILE_CONTENTS),
                ]:
                    path = parent / name
                    path.write_text(contents)
                    path.chmod(0o600)
                output(
                    f'Configuration directory created: {parent!s}.',
                    'Includes example settings files. Edit them to suit your needs.',
                    'Search for and replace any fields delimited with << and >>.',
                    'Delete any configurations you do not need.',
                    'Generally you will use either home or root, but not both.',
                    sep = '\n'
                )
                done()

            path = PythonFile(parent, SETTINGS_FILE)
            settings_filename = path.path
            settings = path.run()

            config = get_config(
                name, settings, self.composite_config_allowed,
                self.show_config_name
            )
            settings['config_name'] = config
            self.config_name = config
            includes = Collection(settings.get(INCLUDE_SETTING))
            includes = [config] + list(includes.values())

        if settings.get('passphrase'):
            if getmod(path) & 0o077:
                warn("file permissions are too loose.", culprit=path)
                codicil(f"Recommend running: chmod 600 {path!s}")

        self.settings.update(settings)

        for include in includes:
            path = to_path(parent, include)
            self.read(path=path)

        # default src_dirs if not given
        if not self.settings.get('src_dirs'):
            self.settings['src_dirs'] = []

        # default archive if not given
        if 'archive' not in self.settings:
            if not 'prefix' in self.settings:
                self.settings['prefix'] = '{host_name}-{user_name}-{config_name}-'
            self.settings['archive'] = self.settings['prefix'] + '{{now}}'

    # check() {{{2
    def check(self):
        # gather the string valued settings together (can be used by resolve)
        self.str_settings = {k:v for k, v in self.settings.items() if is_str(v)}

        # complain about required settings that are missing
        missing = []
        required_settings = 'repository'.split()
        for each in required_settings:
            if not self.settings.get(each):
                missing.append(each)
        if missing:
            missing = conjoin(missing)
            raise Error(f'{missing}: no value given for setting.')

    # resolve {{{2
    def resolve(self, value):
        # escape any double braces
        try:
            value = value.replace('{{', r'\b').replace('}}', r'\e')
        except AttributeError:
            if isinstance(value, int) and not isinstance(value, bool):
                return str(value)
            return value

        # expand names contained in braces
        try:
            resolved = value.format(
                host_name=hostname, user_name=username, prog_name=PROGRAM_NAME,
                **self.str_settings
            )
        except KeyError as e:
            raise Error('unknown setting.', culprit=e)
        if resolved != value:
            resolved = self.resolve(resolved)

        # restore escaped double braces with single braces
        return resolved.replace(r'\b', '{').replace(r'\e', '}')

    # resolve_path {{{2
    def resolve_path(self, value, parent_dir=None):
        if parent_dir:
            return to_path(parent_dir, self.resolve(value))
        return to_path(self.resolve(value))

    # handle errors {{{2
    def fail(self, *msg, comment=''):
        msg = full_stop(' '.join(str(m) for m in msg))
        try:
            if self.notify and not Color.isTTY():
                Run(
                    ['mail', '-s', f'{PROGRAM_NAME} on {hostname}: {msg}'] + self.notify.split(),
                    stdin=dedent(f'''
                        {msg}
                        {comment}
                        config = {self.config_name}
                        source = {username}@{hostname}:{', '.join(str(d) for d in self.src_dirs)}
                        destination = {self.repository}
                    ''').lstrip(),
                    modes='soeW'
                )
        except Error:
            pass
        try:
            if self.notifier and not Color.isTTY():
                Run(
                    self.notifier.format(
                        msg=msg, hostname=hostname,
                        user_name=username, prog_name=PROGRAM_NAME,
                    ),
                    modes='soeW'
                )
        except Error:
            pass
        except KeyError as e:
            warn('unknown key.', culprit=(self.settings_file, 'notifier', e))

    # get resolved value {{{2
    def value(self, name, default=''):
        """Gets fully resolved value of string setting."""
        return self.resolve(self.settings.get(name, default))

    # get resolved values {{{2
    def values(self, name):
        """Iterate though fully resolved values of a collection setting."""
        for value in Collection(self.settings.get(name)):
            yield self.resolve(value)

    # borg_options() {{{2
    def borg_options(self, cmd, options, strip_prefix=True):
        # handle special cases first {{{3
        args = []
        if self.value('verbose'):
            options = list(options)
            options.append('verbose')
        if 'verbose' in options:
            args.append('--verbose')
        if 'trial-run' in options and cmd in borg_commands_with_dryrun.split():
            args.append('--dry-run')
        if cmd == 'create':
            if 'verbose' in options:
                args.append('--list')
                if 'trial-run' not in options:
                    args.append('--stats')
            for path in render_paths(self.values('excludes')):
                args.extend(['--exclude', path])
            exclude_from = self.value('exclude_from')
            if exclude_from:
                if is_str(exclude_from):
                    exclude_from = [exclude_from]
                for each in exclude_from:
                    path = to_path(self.config_dir, each)
                    if not path.exists():
                        raise Error('--exclude-from file does not exist.', culprit=path)
                    args.extend(['--exclude-from', str(path)])

        if cmd == 'extract':
            if 'verbose' in options:
                args.append('--list')

        if cmd == 'init':
            if self.passphrase or self.avendesora_account:
                encryption = self.encryption if self.encryption else 'repokey'
                args.append(f'--encryption={encryption}')
                if encryption == 'none':
                    warn('passphrase given but not needed as encryption set to none.')
                if encryption in 'keyfile keyfile-blake2'.split():
                    warn(
                        "you should use 'borg key export' to export the",
                        "encryption key, and then keep that key in a safe",
                        "place.  If you lose the key you will lose access to",
                        "your backups.",
                        wrap=True
                    )
            else:
                encryption = self.encryption if self.encryption else 'none'
                if encryption != 'none':
                    raise Error('passphrase not specified.')
                args.append(f'--encryption={encryption}')

        # add the borg command line options appropriate to this command {{{3
        for name, attrs in BORG_SETTINGS.items():
            if strip_prefix and name == 'prefix':
                continue
            if cmd in attrs['cmds'] or 'all' in attrs['cmds']:
                opt = convert_name_to_option(name)
                val = self.value(name)
                if val:
                    if 'arg' in attrs and attrs['arg']:
                        args.extend([opt, str(val)])
                    else:
                        args.extend([opt])
        return args

    # publish_passcode() {{{2
    def publish_passcode(self):
        passcommand = self.passcommand
        passcode = self.passphrase

        # process passcomand
        if passcommand:
            if passcode:
                warn('passphrase unneeded.', culprit='passcommand')
                return dict(BORG_PASSCOMMAND = passcommand)

        # get passphrase from avendesora
        if not passcode and self.avendesora_account:
            narrate('running avendesora to access passphrase.')
            try:
                from avendesora import PasswordGenerator
                pw = PasswordGenerator()
                account = pw.get_account(self.value('avendesora_account'))
                field = self.value('avendesora_field', None)
                passcode = str(account.get_value(field))
            except ImportError:
                raise Error(
                    'Avendesora is not available',
                    'you must specify passphrase in settings.',
                    sep = ', '
                )

        if passcode:
            return dict(BORG_PASSPHRASE = passcode)

        if self.encryption is None:
            self.encryption = 'none'
        if self.encryption == 'none':
            narrate('passphrase is not available, encryption disabled.')
            return {}
        raise Error('Cannot determine the encryption passphrase.')

    # run_borg() {{{2
    def run_borg(self, cmd, args='', borg_opts=None, emborg_opts=(), strip_prefix=False):

        # prepare the command
        os.environ.update(self.publish_passcode())
        os.environ['BORG_DISPLAY_PASSPHRASE'] = 'no'
        if self.ssh_command:
            os.environ['BORG_RSH'] = self.ssh_command
        executable = self.value('borg_executable', BORG)
        if borg_opts is None:
            borg_opts = self.borg_options(cmd, emborg_opts, strip_prefix)
        command = (
            [executable]
          + cmd.split()
          + borg_opts
          + (args.split() if is_str(args) else args)
        )
        environ = {k:v for k, v in os.environ.items() if k.startswith('BORG_')}
        if 'BORG_PASSPHRASE' in environ:
            environ['BORG_PASSPHRASE'] = '<redacted>'
        narrate('setting environment variables:', render(environ))

        # check if ssh agent is present
        if self.needs_ssh_agent:
            for ssh_var in 'SSH_AGENT_PID SSH_AUTH_SOCK'.split():
                if ssh_var not in os.environ:
                    warn(
                        'environment variable not found, is ssh-agent running?',
                        culprit=ssh_var
                    )

        # run the command
        narrate('running:\n{}'.format(
            indent(render_command(command, borg_options_arg_count))
        ))
        starts_at = arrow.now()
        narrate('starts at: {!s}'.format(starts_at))
        narrating = (
            '--verbose' in borg_opts or
            'verbose' in emborg_opts or
            'narrate' in emborg_opts
        ) and not '--json' in command
        modes = 'soeW' if narrating else 'sOEW'
        borg = Run(command, modes=modes, stdin='', env=os.environ, log=False)
        ends_at = arrow.now()
        narrate('ends at: {!s}'.format(ends_at))
        narrate('elapsed = {!s}'.format(ends_at-starts_at))
        return borg

    # run_borg_raw() {{{2
    def run_borg_raw(self, args):

        # prepare the command
        os.environ.update(self.publish_passcode())
        os.environ['BORG_DISPLAY_PASSPHRASE'] = 'no'
        executable = self.value('borg_executable', BORG)
        remote_path = self.value('remote_path')
        remote_path = ['--remote-path', remote_path] if remote_path else []
        repository = str(self.repository)
        command = (
            [executable] + remote_path + [
                (repository if a == '@repo' else a) for a in args
            ]
        )

        # run the command
        narrate('running:\n{}'.format(
            indent(render_command(command, borg_options_arg_count))
        ))
        starts_at = arrow.now()
        narrate('starts at: {!s}'.format(starts_at))
        borg = Run(command, modes='soeW', env=os.environ, log=False)
        ends_at = arrow.now()
        narrate('ends at: {!s}'.format(ends_at))
        narrate('elapsed = {!s}'.format(ends_at-starts_at))
        return borg

    # destination() {{{2
    def destination(self, archive=None):
        repository = str(self.repository)
        if archive is True:
            archive = self.value('archive')
            if not archive:
                raise Error('archive: setting value not given.')
        if archive:
            return f'{repository}::{archive}'
        else:
            return repository

    # get attribute {{{2
    def __getattr__(self, name):
        return self.settings.get(name)

    # iterate through settings {{{2
    def __iter__(self):
        for key in sorted(self.settings.keys()):
            yield key, self.settings[key]

    # enter {{{2
    def __enter__(self):
        # resolve src directories
        self.src_dirs = [self.resolve_path(d) for d in self.src_dirs]

        # resolve repository
        self.repository = self.resolve_path(self.repository)

        # resolve other files and directories
        data_dir = self.resolve_path(DATA_DIR)
        self.data_dir = data_dir

        if not data_dir.exists():
            # data dir does not exist, create it
            self.data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        self.logfile = self.resolve_path(LOG_FILE, data_dir)

        if 'no-log' not in self.options:
            self.prev_logfile = self.resolve_path(PREV_LOG_FILE, data_dir)
            rm(self.prev_logfile)
            if self.logfile.exists():
                mv(self.logfile, self.prev_logfile)

        self.date_file = self.resolve_path(DATE_FILE, data_dir)

        # perform locking
        lockfile = self.lockfile = self.resolve_path(LOCK_FILE, data_dir)
        if self.requires_exclusivity:
            # check for existence of lockfile
            if lockfile.exists():
                raise Error(f'currently running (see {lockfile} for details).')

            # create lockfile
            now = arrow.now()
            pid = os.getpid()
            lockfile.write_text(dedent(f'''
                started = {now!s}
                pid = {pid}
            ''').lstrip())

        # open logfile
        if 'no-log' not in self.options:
            get_informer().set_logfile(self.logfile)

        return self

    # exit {{{2
    def __exit__(self, exc_type, exc_val, exc_tb):
        # delete lockfile
        if self.requires_exclusivity:
            self.lockfile.unlink()
