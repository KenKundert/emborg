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
import arrow
import pwd
import os
import socket
import nestedtext as nt
from inform import Error, narrate, os_error, warn
from .shlib import Run, set_prefs as set_shlib_prefs
set_shlib_prefs(use_inform=True, log_cmd=True)


# gethostname {{{1
# returns short version of the hostname (the hostname without any domain name)
def gethostname():
    return socket.gethostname().split(".")[0]


def getfullhostname():
    return socket.gethostname()


# getusername {{{1
def getusername():
    return pwd.getpwuid(os.getuid()).pw_name


# pager {{{1
def pager(text):
    program = os.environ.get("PAGER", "less")
    Run([program], stdin=text, modes="Woes")


# two_columns {{{1
def two_columns(col1, col2, width=16, indent=True):
    indent = "    "
    if len(col1) > width:
        return "%s%s\n%s%s%s" % (indent, col1, indent, "  " + width * " ", col2)
    else:
        return "%s%-*s  %s" % (indent, width, col1, col2)


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
    return filename, "line %s" % line

# when {{{1
def when(time, relative_to=None, as_past=None, as_future=None):
    """Converts time into a human friendly description of a time difference

    Takes a time and returns a string that is intended for people.  It is a
    short description of the time difference between the given time and the
    current time or a reference time.  It is like arrow.humanize(), but provides
    more resolution.  It is suitable for use with time differences that exceed
    1 second.  Any smaller than that will round to 0.

    Arguments:
        time (datetime):
            The time of the event. May either be in the future or the past.
        relative_to (datetime):
            Time to compare against to form the time difference.  If not given,
            the current time is used.
        as_ast (bool or str):
            If true, the word “ago” will be added to the end of the returned
            time difference if it is negative, indicating it occurred in the
            past.  It it a string, it should contain ‘{}’, which is replaced
            with the time difference.
        as_future (bool or str):
            If true, the word “in” will be added to the front of the returned
            time difference if it is positive, indicating it occurs in the
            past.  It it a string, it should contain ‘{}’, which is replaced
            with the time difference.
    Returns:
        A user friendly string that describes the time difference.

    Examples:

        >>> import arrow
        >>> now = arrow.now()
        >>> print(when(now.shift(seconds=60.1)))
        1 minute

        >>> print(when(now.shift(seconds=2*60), as_future=True))
        in 2 minutes

        >>> print(when(now.shift(seconds=-60*60), as_past=True))
        60 minutes ago

        >>> print(when(now.shift(seconds=3.5*60), as_future="{} from now"))
        3.5 minutes from now

        >>> print(when(now.shift(days=-2*365), as_past="last run {} ago"))
        last run 2 years ago
    """

    if relative_to is None:
        relative_to = arrow.now()
    difference = time - relative_to
    seconds = 60*60*24*difference.days + difference.seconds

    def fmt(dt, prec, unit):
        if prec:
            num = f'{dt:0.1f}'
            if num.endswith('.0'):
                num = num[:-2]
        else:
            num = f'{dt:0.0f}'
        if num == '1':
            offset = f'{num} {unit}'
        else:
            offset = f'{num} {unit}s'
        return offset

    if seconds < 0 and as_past:
        if as_past is True:
            as_past = "{} ago"

        def annotate(dt, prec, unit):
            return as_past.format(fmt(dt, prec, unit))

    elif seconds >= 0 and as_future:
        if as_future is True:
            as_future = "in {}"

        def annotate(dt, prec, unit):
            return as_future.format(fmt(dt, prec, unit))

    else:
        annotate = fmt

    seconds = abs(seconds)
    if seconds < 60:
        return annotate(seconds, 0, "second")
    minutes = seconds / 60
    if minutes < 10:
        return annotate(minutes, 1, "minute")
    if minutes < 120:
        return annotate(minutes, 0, "minute")
    hours = minutes / 60
    if hours < 10:
        return annotate(hours, 1, "hour")
    if hours < 36:
        return annotate(hours, 0, "hour")
    days = hours / 24
    if days < 14:
        return annotate(days, 1, "day")
    weeks = days / 7
    if weeks < 8:
        return annotate(weeks, 0, "week")
    months = days / 30
    if months < 18:
        return annotate(months, 0, "month")
    years = days / 365
    if years < 10:
        return annotate(years, 1, "year")
    return annotate(years, 0, "year")


# update_latest {{{1
def update_latest(command, path, repo_size=None):
    narrate(f"updating date file for {command}: {str(path)}")
    latest = {}
    try:
        latest = nt.load(path, dict)
    except nt.NestedTextError as e:
        warn(e)
    except FileNotFoundError:
        pass
    except OSError as e:
        warn(os_error(e))
    latest[f"{command} last run"] = str(arrow.now())
    if repo_size:
        latest['repository size'] = repo_size
    elif 'repository size' in latest:
        if repo_size is False:
            del latest['repository size']

    try:
        nt.dump(latest, path, sort_keys=True)
    except nt.NestedTextError as e:
        warn(e)
    except OSError as e:
        warn(os_error(e))

# read_latest {{{1
def read_latest(path):
    try:
        latest = nt.load(path, dict)
        for k, v in latest.items():
            if "last run" in k:
                try:
                    latest[k] = arrow.get(v)
                except arrow.parser.ParserError:
                    warn(f"{k}: date not given in iso format.", culprit=path)
        return latest
    except nt.NestedTextError as e:
        raise Error(e)
    except OSError as e:
        raise Error(os_error(e))
