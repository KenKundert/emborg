Releases
========

**Latest development release**:
    | Version: 1.5.0
    | Released: 2019-09-30

**1.5 (2019-09-30)**:
    - Added composite configurations.
    - Added support for multiple backup configurations in a single repository.
    - Added *prefix*, *exclude_from*, and *verbose* settings.
    - Provide default value for *archive* setting.
    - Add --all command line option to *mount* command.
    - Add --include-external command line option to *check*, *list*, *mount*, 
      and *prune* commands.
    - Add --sort command line option to *manifest* command.
    - Add --latest command line option to *delete* command.
    - Added --quiet option
    - *umount* command now deletes directory used as mount point.
    - Moved log files to ~/.local/share/emborg (run 'mv 
      ~/.config/emborg/\*.{log,lastbackup}\* ~/.local/share/emborg' before using 
      this version).

**1.4 (2019-04-24)**:
    - Added *ssh_command* setting
    - Added --fast option to *info* command
    - Added *emborg-overdue* executable
    - Allow 'run_before_backup' and 'run_after_backup' to be simple strings

**1.3 (2019-01-16)**:
    - Added the raw *borg* command

**1.2 (2019-01-16)**:
    - Added the borg_executable and passcommand

**1.1 (2019-01-13)**:
    - Improved and documented API.
    - Creates the settings directory if it is missing and add example files.
    - Added --mute option.
    - Support multiple email addresses in *notify*.
    - Added warning if settings file is world readable and contains a passphrase.

**1.0 (2019-01-09)**:
    - added *remote_path* setting.
    - formal public release.

**0.3 (2018-12-25)**:
    - initial public release (beta).

**0.0 (2018-12-05)**:
    - initial release (alpha).
