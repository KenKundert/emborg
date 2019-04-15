# Utilities

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
from shlib import Run, to_path
from inform import is_str
from pipes import quote
import os
import shlex
import socket
import pwd

# gethostname {{{1
# returns short version of the hostname (the hostname without any domain name)
def gethostname():
    return socket.gethostname().split('.')[0]

# getusername {{{1
def getusername():
    return pwd.getpwuid(os.getuid()).pw_name

# pager {{{1
def pager(text):
    program = os.environ.get('PAGER', 'less')
    Run([program], stdin=text, modes='Woes')

# two_columns {{{1
def two_columns(col1, col2, width=16, indent=True):
    indent = '    '
    if len(col1) > width:
        return '%s%s\n%s%s%s' % (
            indent, col1, indent, '  '+width*' ', col2
        )
    else:
        return '%s%-*s  %s' % (indent, width, col1, col2)

# error_source {{{1
def error_source():
    """Source of error
    Reads stack trace to determine filename and line number of error.
    """
    import traceback
    try:
        # return filename and lineno
        # context and content are also available
        import sys
        exc_cls, exc, tb = sys.exc_info()
        trace = traceback.extract_tb(tb)
        filename, line, context, text = trace[-1]
    except SyntaxError:
        # extract_stack() does not work on binary encrypted files. It generates
        # a syntax error that indicates that the file encoding is missing
        # because the function tries to read the file and sees binary data. This
        # is not a problem with ascii encrypted files as we don't actually show
        # code, which is gibberish, but does not require an encoding. In this
        # case, extract the line number from the trace.
        from .gpg import get_active_python_file
        filename = get_active_python_file()
        line = tb.tb_next.tb_lineno
    return filename, 'line %s' % line

# render_command {{{1
def render_command(cmd, option_args=True):
    if is_str(cmd):
        cmd = shlex.split(cmd)
    else:
        cmd = [str(c) for c in cmd]
            # Cannot use to_str() because it can change some arguments when not intended.
            # This is particularly problematic the duplicify arguments in emborg.

    if option_args is True:
        duplicity_option_args = {
            '--gpg-binary': 1,
            '--log-file': 1,
            '--archive-dir': 1,
            '--name': 1,
            '--sftp-command': 1,
            '--file-to-restore': 1,
            '--ssh-backend': 1,
            '--exclude': 1,
            '--time': 1,
        }
        option_args = duplicity_option_args

    cmd.reverse()
    lines = []
    while cmd:
        opt = cmd.pop()
        num_args = option_args.get(opt, 0)
        argument = [opt]
        for i in range(num_args):
            argument.append(quote(cmd.pop()))
        lines.append(' '.join(argument))
    return ' \\\n    '.join(lines)

# render_path() {{{1
def render_path(path):
    return str(to_path(path))

# render_paths() {{{1
def render_paths(path_list):
    return [render_path(path) for path in path_list]
