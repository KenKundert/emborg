# Emborg Preferences
#
# Copyright (C) 2018-2024 Kenneth S. Kundert

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
from .shlib import to_path
from appdirs import user_config_dir, user_data_dir
from inform import dedent

# Preferences {{{1
# Constants {{{2
PROGRAM_NAME = "emborg"
DEFAULT_COMMAND = "create"
INDENT = "    "
BORG = "borg"

# The default configuration directories for both Microsoft and Apple are not
# always preferred by users, whereas the directory used by Linux
# (~/.config/emborg) seems to have universal appeal.  So, use the Linux path if
# it exists and backstop with the system preferred location.
config_dir = to_path("~/.config/emborg")
if config_dir.exists():
    CONFIG_DIR = str(config_dir)
else:
    CONFIG_DIR = user_config_dir(PROGRAM_NAME)
DATA_DIR = user_data_dir(PROGRAM_NAME)

SETTINGS_FILE = "settings"
OVERDUE_FILE = "overdue.conf"
LOG_FILE = "{config_name}.log"
OVERDUE_LOG_FILE = "overdue.log"
PREV_LOG_FILE = "{config_name}.log.prev"
LOCK_FILE = "{config_name}.lock"
DATE_FILE = "{config_name}.latest.nt"

CONFIGS_SETTING = "configurations"
DEFAULT_CONFIG_SETTING = "default_configuration"
INCLUDE_SETTING = "include"
DEFAULT_ENCODING = "utf-8"

# Emborg settings {{{2
EMBORG_SETTINGS = dict(
    archive="template Borg should use when creating archive names",
    avendesora_account="account name that holds passphrase for encryption key in Avendesora",
    avendesora_field="name of field in Avendesora that holds the passphrase",
    borg_executable="path to borg",
    check_after_create="run check as the last step of an archive creation",
    cmd_name="name of Emborg command being run (read only)",
    colorscheme="the color scheme",
    config_dir="absolute path to configuration directory (read-only)",
    config_name="name of active configuration (read only)",
    configurations="available Emborg configurations",
    default_configuration="default Emborg configuration",
    default_mount_point="directory to use as mount point if one is not specified",
    do_not_expand="names of settings that must not undergo setting evaluation",
    encoding="encoding when talking to borg",
    encryption="encryption method (see Borg documentation)",
    excludes="list of glob strings of files or directories to skip",
    exclude_from="file that contains exclude patterns",
    home_dir="users home directory (read only)",
    include="include the contents of another file",
    log_dir="emborg log directory (read only)",
    manage_diffs_cmd="command to use to manage differences in files and directories",
    manifest_formats="format strings used by manifest",
    manifest_default_format="the format that manifest should use if none is specified",
    must_exist="if set, each of these files or directories must exist or create will quit with an error",
    needs_ssh_agent="if set, Emborg will complain if ssh_agent is not available",
    notifier="notification program",
    notify="email address to notify when things go wrong",
    passcommand="command used by Borg to acquire the passphrase",
    passphrase="passphrase for encryption key (if specified, Avendesora is not used)",
    patterns="patterns that indicate whether a path should be included or excluded",
    patterns_from="file that contains patterns",
    prune_after_create="run prune after creating an archive",
    compact_after_delete="run compact after deleting an archive or pruning a repository",
    report_diffs_cmd="shell command to use to report differences in files and directories",
    repository="path to remote directory that contains repository",
    run_after_backup="commands to run after archive has been created",
    run_before_backup="commands to run before archive is created",
    run_after_last_backup="commands to run after last archive has been created",
    run_before_first_backup="commands to run before first archive is created",
    run_after_borg="commands to run after last Borg command has run",
    run_before_borg="commands to run before first Borg command is run",
    show_progress="show borg progress when running create command",
    show_stats="show borg statistics when running create, delete, and prune commands",
    src_dirs="the directories to archive",
    ssh_command="command to use for SSH, can be used to specify SSH options",
    verbose="make Borg more verbose",
    working_dir="working directory",
)
# Any setting found in the users settings files that is not found in
# EMBORG_SETTINGS or BORG_SETTINGS is highlighted as a unknown setting by
# the settings command.

# Borg settings {{{2
BORG_SETTINGS = dict(
    append_only = dict(
        cmds = ["init"],
        desc = "create an append-only mode repository"
    ),
    chunker_params = dict(
        cmds = ["create"],
        arg = "PARAMS",
        desc = "specify the chunker parameters"
    ),
    compression = dict(
        cmds = ["create"],
        arg = "COMPRESSION",
        desc = "compression algorithm"
    ),
    exclude_caches = dict(
        cmds = ["create"],
        desc = "exclude directories that contain a CACHEDIR.TAG file"
    ),
    exclude_nodump = dict(
        cmds = ["create"],
        desc = "exclude files flagged NODUMP"
    ),
    exclude_if_present = dict(
        cmds = ["create"],
        arg = "NAME",
        desc = "exclude directories that are tagged by containing a filesystem object with the given NAME",
    ),
    lock_wait = dict(
        cmds = ["all"],
        arg = "SECONDS",
        desc = "wait at most SECONDS for acquiring a repository/cache lock (default: 1)",
    ),
    keep_within = dict(
        cmds = ["prune"],
        arg = "INTERVAL",
        desc = "keep all archives within this time interval"
    ),
    keep_last = dict(
        cmds = ["prune"],
        arg = "NUM",
        desc = "number of the most recent archives to keep"
    ),
    keep_minutely = dict(
        cmds = ["prune"],
        arg = "NUM",
        desc = "number of minutely archives to keep"
    ),
    keep_hourly = dict(
        cmds = ["prune"],
        arg = "NUM",
        desc = "number of hourly archives to keep"
    ),
    keep_daily = dict(
        cmds = ["prune"],
        arg = "NUM",
        desc = "number of daily archives to keep"
    ),
    keep_weekly = dict(
        cmds = ["prune"],
        arg = "NUM",
        desc = "number of weekly archives to keep"
    ),
    keep_monthly = dict(
        cmds = ["prune"],
        arg = "NUM",
        desc = "number of monthly archives to keep"
    ),
    keep_yearly = dict(
        cmds = ["prune"],
        arg = "NUM",
        desc = "number of yearly archives to keep"
    ),
    one_file_system = dict(
        cmds = ["create"],
        desc = "stay in the same file system and do not store mount points of other file systems",
    ),
    remote_path = dict(
        cmds = ["all"],
        arg = "CMD",
        desc = "name of borg executable on remote platform",
    ),
    remote_ratelimit = dict(
        cmds = ["all"],
        arg = "RATE",
        desc = "set remote network upload rate limit in kiB/s (default: 0=unlimited)",
    ),
    sparse = dict(
        cmds = ["create"],
        desc = "detect sparse holes in input (supported only by fixed chunker)"
    ),
    threshold = dict(
        cmds = ["compact"],
        arg = "PERCENT",
        desc = "set minimum threshold in percent for saved space when compacting (default: 10)",
    ),
    umask = dict(
        cmds = ["all"],
        arg = "M",
        desc = "set umask to M (local and remote, default: 0077)"
    ),
    upload_buffer = dict(
        cmds = ["all"],
        arg = "UPLOAD_BUFFER",
        desc = "set network upload buffer size in MiB (default: 0=no buffer)",
    ),
    upload_ratelimit = dict(
        cmds = ["all"],
        arg = "RATE",
        desc = "set rate limit in kiB/s, used when writing to a remote network (default: 0=unlimited)",
    ),
    prefix = dict(
        cmds = ["check", "delete", "info", "list", "mount", "prune"],
        arg = "PREFIX",
        desc = "only consider archive names starting with this prefix",
    ),
    glob_archives = dict(
        cmds = ["check", "delete", "info", "list", "mount", "prune"],
        arg = "GLOB",
        desc = "only consider archive names matching the glob",
    ),
)

# Utilities {{{2
# utility function that converts setting names to borg option names
def convert_name_to_option(name):
    return "--" + name.replace("_", "-")


# Initial contents of files {{{2
INITIAL_SETTINGS_FILE_CONTENTS = dedent(
    """
    # These settings are common to all configurations

    # configurations
    configurations = '⟪list your configurations here⟫'
    default_configuration = '⟪default-config⟫'

    # encryption
    encryption = '⟪encryption⟫'              # borg encryption method
        # Common choices are 'repokey' and 'keyfile'.
        # With 'repokey' the encryption key is copied into repository, use this
        # only if the remote repository is owned by you and is secure.
        # With 'keyfile' the encryption key is only stored locally. Be sure to
        # export it and save a copy in a safe place, otherwise you may not be
        # able to access your backups if you lose your disk.
    # specify either passphrase or avendesora_account
    passphrase = '⟪passcode⟫'                # passphrase for encryption key
    avendesora_account = '⟪account-name⟫'    # avendesora account holding passphrase

    # basic settings
    # specify notify if batch and notifier if interactive
    notify = '⟪your-email-address⟫'          # who to notify when things go wrong
    notifier = 'notify-send -u normal {prog_name} "{msg}"'
                                             # interactive notifier program
    prune_after_create = True                # automatically run prune after a backup
    check_after_create = 'latest'            # automatically run check after a backup
    compact_after_delete = True              # automatically run compact after a delete or prune

    # repository settings
    repository = '⟪host⟫:⟪path⟫/{host_name}-{user_name}-{config_name}'
    archive = '{host_name}-{{now}}'
        # These may contain {<name>} where <name> is any of host_name, user_name,
        # prog_name config_name, or any of the user specified settings.
        # Double up the braces to specify parameters that should be interpreted
        # directly by borg, such as {{now}}.
    compression = 'lz4'

    # filter settings
    exclude_if_present = '.nobackup'
    exclude_caches = True

    # prune settings
    keep_within = '1d'                       # keep all archives created in interval
    keep_hourly = 48                         # number of hourly archives to keep
    keep_daily = 14                          # number of daily archives to keep
    keep_weekly = 8                          # number of weekly archives to keep
    keep_monthly = 24                        # number of monthly archives to keep
    keep_yearly = 2                          # number of yearly archives to keep
    """
).lstrip()

INITIAL_ROOT_CONFIG_FILE_CONTENTS = dedent(
    """
    # Settings for root configuration
    # use of absolute paths is recommended
    src_dirs = '/'           # paths to directories to be backed up
    excludes = '''
        /dev
        /home/*/.cache
        /mnt
        /proc
        /root/.cache
        /run
        /sys
        /tmp
        /var/cache
        /var/run
        /var/tmp
    '''                      # list of files or directories to skip
    """
).lstrip()

INITIAL_HOME_CONFIG_FILE_CONTENTS = dedent(
    """
    # Settings for home configuration
    # use of absolute paths is recommended
    src_dirs = '~'           # absolute path to directory to be backed up
    excludes = '''
        ~/.cache
        **/*~
        **/__pycache__
        **/*.pyc
        **/.*.swp
        **/.*.swo
    '''                      # list of files or directories to skip
    """
).lstrip()
