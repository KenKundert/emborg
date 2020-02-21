# Patterns and Excludes

# License {{{1
# Copyright (C) 2018-2020 Kenneth S. Kundert
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
from os.path import expanduser as expand_user

from inform import Error, error

from shlib import to_path


# Globals {{{1
known_kinds = "PR+-!"
known_styles = "fm sh re pp pf".split()


# check_root() {{{1
def check_root(root, working_dir):
    root = to_path(root)
    if not root.exists():
        raise Error("not found.", culprit=root)
    if not str(root.resolve()).startswith(str(working_dir)):
        raise Error("not in working directory:", working_dir, culprit=root)
    return root.is_absolute()


# check_roots() {{{1
def check_roots(roots, working_dir):
    if not roots:
        raise Error("no roots or source directories given.")
    is_absolute = [check_root(root, working_dir) for root in roots]
    all_are_absolute = all(is_absolute)
    any_are_absolute = any(is_absolute)
    if all_are_absolute != any_are_absolute:
        raise Error(
            "mix of relative and absolute paths used for recursive roots:",
            *roots,
            sep="\n    "
        )
    if any_are_absolute and str(working_dir) != "/":
        raise Error("working directory must be '/' if root paths are absolute.")


# check_pattern() {{{1
def check_pattern(pattern, default_style, roots, expand_tilde):
    if ":" in pattern:
        style, colon, path = pattern.partition(":")
        prefix = style + colon
    else:
        style, path = default_style, pattern
        prefix = ""

    if style not in known_styles:
        raise Error("unknown pattern style.")

    # accept regular expression without further checking
    if style == "re" or path[0] == "*":
        return pattern

    # process leading ~ in path
    if path[0] == "~":
        if expand_tilde:
            path = expand_user(path)
            pattern = prefix + path
        else:
            raise Error("borg does not interpret leading tilde as user.")

    # check to see that path corresponds to a root
    if any(path.startswith(str(root)) for root in roots):
        return pattern
    if style in ["fm", "sh"]:
        if any(str(root).startswith(path.partition("*")[0]) for root in roots):
            return pattern

    raise Error("path is not in a known root.")


# check_patterns() {{{1
def check_patterns(patterns, roots, working_dir, src, expand_tilde=True):
    paths = []
    default_style = "sh"
    for pattern in patterns:
        pattern = pattern.strip()
        culprit = (str(src), repr(pattern))
        kind = pattern[0:1]
        arg = pattern[1:].lstrip()
        if kind in ["", "#"]:
            continue  # is comment
        if kind not in known_kinds:
            error("unknown type", culprit=culprit)
            continue
        if kind == "R":
            try:
                if arg[0] == "~" and not expand_tilde:
                    error(
                        "borg does not interpret leading tilde as user.",
                        culprit=culprit,
                    )
                root = expand_user(arg)
                check_root(root, working_dir)
                roots.append(root)
            except AttributeError:
                error("can no longer add roots.", culprit=culprit)
            paths.append(kind + " " + root)
        elif kind == "P":
            if arg in known_styles:
                default_style = arg
            else:
                error("unknown pattern style.", culprit=culprit)
            paths.append(kind + " " + arg)
        elif not roots:
            error("no roots available.", culprit=culprit)
            return []
        else:
            try:
                paths.append(
                    kind + " " + check_pattern(arg, default_style, roots, expand_tilde)
                )
            except Error as e:
                e.report(culprit=culprit)
    return paths


# check_excludes() {{{1
def check_excludes(patterns, roots, src, expand_tilde=True):
    if not roots:
        error("no roots available.", culprit=src)
        return
    paths = []

    for pattern in patterns:
        pattern = str(pattern).strip()
        if not pattern or pattern[0] == "#":
            continue  # is comment
        try:
            paths.append(check_pattern(pattern, "fm", roots, expand_tilde))
        except Error as e:
            e.report(culprit=(str(src), repr(pattern)))
    return paths


# check_patterns_files() {{{1
def check_patterns_files(filenames, roots, working_dir):
    for filename in filenames:
        patterns = to_path(filename).read_text().splitlines()
        check_patterns(patterns, roots, working_dir, filename, expand_tilde=False)


# check_excludes_files() {{{1
def check_excludes_files(filenames, roots):
    for filename in filenames:
        excludes = to_path(filename).read_text().splitlines()
        check_excludes(excludes, roots, filename, expand_tilde=False)
