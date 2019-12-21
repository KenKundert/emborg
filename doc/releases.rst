Releases
========

**Latest development release**:
    | Version: 1.11.4
    | Released: 2019-12-20

    - added :ref:`default_mount_point` setting.
    - fixed some issues with :ref:`borg <borg>` command.
    - added ``--oldest`` option to :ref:`due <due>` command.

**1.11 (2019-11-27)**:
    - Bug fix release.

**1.10 (2019-11-11)**:
    - Bug fix release.

**1.9 (2019-11-08)**:
    - Added ability to check individual archives to the :ref:`check <check>` command.
    - Made latest archive the default for :ref:`check <check>` command.
    - Allow :ref:`exclude_from <exclude_from>` setting to be a list of file names.

**1.8 (2019-10-12)**:
    - Remove duplicated commands.

**1.7 (2019-10-07)**:
    - Fixed bug that involved the boolean Borg settings
      (:ref:`one_file_system <one_file_system>`, :ref:`exclude_caches <exclude_caches>`, ...)

**1.6 (2019-10-04)**:
    - Added :ref:`restore <restore>` command.
    - Added :ref:`verbose <verbose>` setting.

**1.5 (2019-09-30)**:
    - Added composite configurations.
    - Added support for multiple backup configurations in a single repository.
    - Added :ref:`prefix <prefix>` and :ref:`exclude_from <exclude_from>` settings.
    - Provide default value for :ref:`archive <archive>` setting.
    - Add --all command line option to :ref:`mount <mount>` command.
    - Add --include-external command line option to :ref:`check <check>`, :ref:`list <list>`, 
      :ref:`mount <mount>`, and :ref:`prune <prune>` commands.
    - Add --sort command line option to :ref:`manifest <manifest>` command.
    - Add --latest command line option to :ref:`delete <delete>` command.
    - Added --quiet command line option
    - :ref:`umount <umount>` command now deletes directory used as mount point.
    - Moved log files to ~/.local/share/emborg
      (run 'mv ~/.config/emborg/\*.{log,lastbackup}\* ~/.local/share/emborg' 
      before using this version).

**1.4 (2019-04-24)**:
    - Added *ssh_command* setting
    - Added --fast option to :ref:`info <info>` command
    - Added *emborg-overdue* executable
    - Allow :ref:`run_before_backup <run_before_backup>` and :ref:`run_after_backup <run_after_backup>` to be simple 
      strings

**1.3 (2019-01-16)**:
    - Added the raw :ref:`borg <borg>` command.

**1.2 (2019-01-16)**:
    - Added the :ref:`borg_executable <borg_executable>` and :ref:`passcommand <passcommand>` settings.

**1.1 (2019-01-13)**:
    - Improved and documented API.
    - Creates the settings directory if it is missing and add example files.
    - Added --mute command line option.
    - Support multiple email addresses in :ref:`notify <notify>`.
    - Added warning if settings file is world readable and contains a passphrase.

**1.0 (2019-01-09)**:
    - added :ref:`remote_path <remote_path>` setting.
    - formal public release.

**0.3 (2018-12-25)**:
    - initial public release (beta).

**0.0 (2018-12-05)**:
    - initial release (alpha).
