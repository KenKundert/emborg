# Help
# Output a help topic.

# License {{{1
# Copyright (C) 2018 Kenneth S. Kundert
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see http://www.gnu.org/licenses/.


# Imports {{{1
from .command import Command
from .utilities import pager, two_columns
from inform import error, output, Error
from textwrap import dedent


# HelpMessage base class {{{1
class HelpMessage(object):
    # get_name() {{{2
    @classmethod
    def get_name(cls):
        try:
            return cls.name.lower()
        except AttributeError:
            # consider converting lower to upper case transitions in __name__ to
            # dashes.
            return cls.__name__.lower()

    # topics {{{2
    @classmethod
    def topics(cls):
        for sub in cls.__subclasses__():
            yield sub

    # show {{{2
    @classmethod
    def show(cls, name=None):
        if name:
            # search commands
            try:
                command, _ = Command.find(name)
                if command:
                    return pager(command.help())
            except Error:
                pass

            # search topics
            for topic in cls.topics():
                if name == topic.get_name():
                    return pager(topic.help())

            error('topic not found.', culprit=name)
        else:
            from .main import synopsis
            cls.help(synopsis)

    # summarize {{{2
    @classmethod
    def summarize(cls, width=16):
        summaries = []
        for topic in sorted(cls.topics(), key=lambda topic: topic.get_name()):
            summaries.append(two_columns(topic.get_name(), topic.DESCRIPTION))
        return '\n'.join(summaries)

    # help {{{2
    @classmethod
    def help(cls, desc):
        if desc:
            output(desc.strip() + '\n')

        output('Available commands:')
        output(Command.summarize())

        output('\nAvailable topics:')
        output(cls.summarize())


# Overview class {{{1
class Overview(HelpMessage):
    DESCRIPTION = "overview of emborg"

    @staticmethod
    def help():
        text = dedent("""
            Emborg is a simple command line utility to orchestrate backups.  It
            is built on Borg, which is a powerful and fast de-duplicating backup
            utility for managing encrypted backups, however it can be rather
            clumsy to use directly.  With Emborg, you specify all the details
            about your backups once in advance, and then use a very simple
            command line interface for your day-to-day activities.  The details
            are contained in ~/.config/emborg.  That directory will contain a
            file (settings) that contains shared settings, and then another file
            for each of your backup configurations.

            Use of Emborg does not preclude the use of Borg directly on the same
            repository.  The philosophy of Emborg is to provide commands that
            you would use often and in an interactive manner with the
            expectation that you would use Borg directly for the remaining
            commands.
        """).strip()
        return text


# Precautions class {{{1
class Precautions(HelpMessage):
    DESCRIPTION = "what everybody should know before using emborg"

    @staticmethod
    def help():
        text = dedent("""
            You should assure you have a backup copy of the encryption
            passphrase in a safe place.  This is very important. If the only
            copy of the passphrase is on the disk being backed up and that disk
            were to fail you would not be able to access your backups.
            I recommend the use of sparekeys (https://github.com/kalekundert/sparekeys)
            as a way of assuring that you always have access to the essential
            information, such as your Borg passphrase and keys, that you would
            need to get started after a catastrophic loss of your disk.

            In addition it is important to understand the your backup data is
            not encrypted with your passphrase, rather your passphrase encrypts
            a key, and your backup data is encrypted with the key.  Thus, your
            backup files cannot be decrypted without both the passphrase and the
            key.  If you choose encryption=repokey then Borg copies your key to
            the remote repository, so you do not need to keep a copy yourself.
            Using repokey is appropriate if you control the server that holds
            the remote repository.  If you choose encryption=keyfile, which is
            appropriate if you do not control the resository's server, then it
            does not copy the key to the repository, so it is essential
            that you export and keep a copy of the key in a safe place.
            Sparekeys can do this for you.

            If you keep the passphrase in a settings file, you should set
            its permissions so that it is not readable by others:

                chmod 700 ~/.config/emborg/settings

            Better yet is to simply not store the passphrase.  This can be
            arranged if you are using Avendesora
            (https://github.com/KenKundert/avendesora), which is a flexible
            password management system. The interface to Avendesora is already
            built in to Emborg, but its use is optional (it need not be
            installed).

            It is also best, if it can be arranged, to keep your backups at a
            remote site so that your backups do not get destroyed in the same
            disaster, such as a fire or flood, that claims your original files.
            One option is rsync.net (https://www.rsync.net/products/attic.html).
            Another is `BorgBase (https://www.borgbase.com).

            Finally, it is a good idea to practice a recovery. Pretend that you
            have lost all your files and then see if you can do a restore from
            backup. Doing this and working out the kinks before you lose your
            files can save you if you ever do lose your files.
        """).strip()
        return text
