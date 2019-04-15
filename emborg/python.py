#
# Read and Write Python files
#
# Package for reading and writing Python files.

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
from shlib import to_path, cp
from inform import display, Error, narrate, os_error, full_stop


# PythonFile class {{{1
class PythonFile:
    ActivePythonFile = None

    @classmethod
    def get_active_python_file(cls):
        return cls.ActivePythonFile

    def __init__(self, *path_components):
        self.path = to_path(*path_components)

    def save(self, contents):
        path = self.path
        path.write_text(contents, encoding='utf-8')

    def read(self):
        path = self.path
        return path.read_text(encoding='utf-8')

    def remove(self):
        self.path.unlink()

    def backup(self, extension):
        """Creates a backup copy of the file.

        The name of the new file has the specified extension prepended to the
        existing suffixes.
        """
        # prepend extension to list of suffixes
        suffixes = self.path.suffixes
        stem = self.path.stem.partition('.')[0]  # remove all suffixes
        new = to_path(self.path.parent, ''.join([stem, extension] + suffixes))
        self.backup_path = new

        cp(self.path, new)
        return new

    def restore(self):
        "Restores the backup copy of the file."
        cp(self.backup_path, self.path)

    def run(self):
        self.ActivePythonFile = self.path
        path = self.path
        narrate('reading:', path)
        try:
            self.code = self.read()
                # need to save the code for the new command
        except OSError as err:
            raise Error(os_error(err))

        try:
            compiled = compile(self.code, str(path), 'exec')
        except SyntaxError as err:
            culprit = (err.filename, err.lineno)
            if err.text is None or err.offset is None:
                raise Error(full_stop(err.msg), culprit=culprit)
            else:
                raise Error(
                    err.msg + ':', err.text.rstrip(), (err.offset-1)*' ' + '^',
                    culprit=culprit, sep='\n'
                )

        contents = {}
        try:
            exec(compiled, contents)
        except Exception as err:
            from .utilities import error_source
            raise Error(full_stop(err), culprit=error_source())
        self.ActivePythonFile = None
        # strip out keys that start with '__' and return them
        return {k: v for k, v in contents.items() if not k.startswith('__')}

    def create(self, contents):
        path = self.path
        try:
            if path.exists():
                # file creation (init) requested, but file already exists
                # don't overwrite the file, instead read it so the information
                # can be used to create any remaining files.
                display("%s: already exists." % path)
                return
            # create the file
            display('%s: creating.' % path)
            # file is not encrypted
            with path.open('wb') as f:
                f.write(contents.encode('utf-8'))
        except OSError as err:
            raise Error(os_error(err))

    def exists(self):
        return self.path.exists()

    def __str__(self):
        return str(self.path)
