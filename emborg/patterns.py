# Patterns and Excludes

# License {{{1
# Copyright (C) 2018-2022 Kenneth S. Kundert
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
from inform import Error, error, log
from .shlib import to_path


# Globals {{{1
known_kinds = "PR+-!"
known_styles = "fm sh re pp pf".split()


# check_root() {{{1
def check_root(root, working_dir):
    if str(root) == '.':
        log(
            "Unable to determine whether paths are contained in a root,",
            "because '.' is a root."
        )
    abs_root = working_dir / root
    if not abs_root.exists():
        raise Error("not found.", culprit=root)
    # the following is a bit cleaner, but no available until python 3.9
    #if not abs_root.is_relative_to(working_dir):
    #    raise Error("not in working directory:", working_dir, culprit=root)
    try:
        abs_root.relative_to(working_dir)
    except ValueError:
        raise Error("not in working directory:", working_dir, culprit=root)
    return to_path(root).is_absolute()


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
            raise Error(
                "do not use leading ~,",
                "borg does not treat it as a user home directory.",
            )

    # check to see that path corresponds to a root
    path = str(to_path(path))
    if any(path.startswith(str(root)) for root in roots):
        return pattern
    if style in ["fm", "sh"]:
        if any(str(root).startswith(path.partition("*")[0]) for root in roots):
            return pattern
    if any(str(root) == '.' for root in roots):
        # cannot check paths if root is '.'
        return pattern
    raise Error("path is not in a known root.")


# check_patterns() {{{1
def check_patterns(
    patterns, roots, working_dir, src, expand_tilde=True, skip_checks=False
):
    paths = []
    default_style = "sh"
    for pattern in patterns:
        pattern = pattern.strip()
        culprit = src
        codicil = repr(pattern)
        kind = pattern[0:1]
        arg = pattern[1:].lstrip()
        if kind in ["", "#"]:
            continue  # is comment
        if kind not in known_kinds:
            error("unknown type", culprit=culprit)
            continue
        if kind == "R":
            if arg[0] == "~" and not expand_tilde:
                error(
                    "borg does not interpret leading tilde as user.",
                    culprit=culprit, codicil=codicil
                )
            root = expand_user(arg)
            if not skip_checks:
                check_root(root, working_dir)
            roots.append(to_path(root))
            paths.append(kind + " " + root)
        elif kind == "P":
            if arg in known_styles:
                default_style = arg
            else:
                error("unknown pattern style.", culprit=culprit, codicil=codicil)
            paths.append(kind + " " + arg)
        elif not roots:
            error("no roots available.", culprit=culprit, codicil=codicil)
            return []
        else:
            try:
                paths.append(
                    kind + " " + check_pattern(arg, default_style, roots, expand_tilde)
                )
            except Error as e:
                e.report(culprit=culprit, codicil=codicil)
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
            e.report(culprit=src, codicil=repr(pattern))
    return paths


# check_patterns_files() {{{1
def check_patterns_files(filenames, roots, working_dir, skip_checks=False):
    for filename in filenames:
        patterns = to_path(filename).read_text().splitlines()
        check_patterns(
            patterns, roots, working_dir, filename,
            expand_tilde=False, skip_checks=skip_checks
        )


# check_excludes_files() {{{1
def check_excludes_files(filenames, roots):
    for filename in filenames:
        excludes = to_path(filename).read_text().splitlines()
        check_excludes(excludes, roots, filename, expand_tilde=False)
