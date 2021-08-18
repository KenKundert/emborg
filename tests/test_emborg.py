# Test Emborg
#
# These tests require BorgBackup to be available.  As such, they are not really
# suitable for public continuous integration services such as GitHub Actions.

# Imports {{{1
import nestedtext as nt
import os
import parametrize_from_file
import pytest
import re
from inform import is_str, Color, Error, indent
from shlib import Run, cd, cp, cwd, ln, lsf, mkdir, rm, set_prefs, touch
from textwrap import dedent
from voluptuous import Schema, Optional, Required, Any
parametrize = parametrize_from_file


# Globals {{{1
# uses local versions of emborg (../bu) and emborg_overdue (../od)
emborg_exe = "../bu".split()
emborg_overdue_exe = "../od".split()
# uses installed code
#emborg_exe = "emborg".split()
#emborg_overdue_exe = "emborg-overdue".split()
set_prefs(use_inform=True)
tests_dir = __file__.rpartition('/')[0]
tests_dir_wo_slash = tests_dir.strip('/')
    # remove the leading and trailing slashes
    # they will be added back in tests if needed

# schema for test cases {{{2
emborg_schema = Schema({
    Optional('opts', default=""): str,
    Optional('args', default=[]): Any(str, list),
    Optional('expected', default=""): str,
    Optional('expected_re', default=""): str,
    Optional('cmp_dirs', default=""): str,
    Optional('rm', default=""): str,
}, required=True)
emborg_overdue_schema = Schema({
    Optional('conf', default=""): str,
    Optional('args', default=[]): Any(str, list),
    Required('expected', default=""): str,
}, required=True)

# EmborgTester class {{{1
class EmborgTester(object):
    # constructor {{{2
    def __init__(self, opts, args, expected, expected_re, cmp_dirs, rm):
        # expected == None implies that another test method is to be used if
        #     available, otherwise the run should not fail.
        # expected == 'FAILURE' implies that the run should fail.
        # expected == <str> implies stdout should match the string precisely
        # expected_re is a regular expression that should match stdout in full
        # cmp_dirs is a pair of directories that should match exactly

        # expand «TESTS»
        if args:
            args = args.replace("«TESTS»", tests_dir_wo_slash)
        if expected:
            expected = expected.replace("«TESTS»", tests_dir_wo_slash)
        if expected_re:
            expected_re = expected_re.replace("«TESTS»", tests_dir_wo_slash)
        if cmp_dirs:
            cmp_dirs = cmp_dirs.replace("«TESTS»", tests_dir_wo_slash)

        self.args = args.split() if is_str(args) else args
        self.expected = expected
        if expected:
            self.expected = expected
        self.expected_re = expected_re
        if expected_re:
            self.expected_re = expected_re
        self.cmp_dirs = cmp_dirs.split() if is_str(cmp_dirs) else cmp_dirs
        self.cmd = emborg_exe + self.args
        self.command = " ".join(self.cmd)
        self.rm = rm
        self.diffout = None

    # run() {{{2
    def run(self):
        try:
            if self.rm:
                rm(self.rm.split())
            emborg = Run(self.cmd, "sOEW")
            self.result = dedent(Color.strip_colors(emborg.stdout)).strip("\n")
            if self.expected:
                return self.expected == self.result
            if self.expected_re:
                return bool(re.fullmatch(self.expected_re, self.result))
            if self.cmp_dirs:
                gen_dir, ref_dir = self.cmp_dirs
                self.expected = ''
                try:
                    diff = Run(["diff", "--recursive", gen_dir, ref_dir], "sOMW")
                    self.result = diff.stdout
                    return True
                except Error as e:
                    self.result = e.stdout
                    return False
            if self.expected == 'FAILURE':
                return False  # this test was expected to raise an exception
            return self.result == ""
        except Error as e:
            self.result = str(e)
            return self.expected == 'FAILURE'

    # get_expected() {{{2
    def get_expected(self):
        if self.expected:
            expected = self.expected
        elif self.expected_re:
            expected = self.expected_re
        else:
            expected = str(self.expected)
        if "\n" in expected:
            return "\n" + indent(expected, stops=2)
        else:
            return expected

    # get_result() {{{2
    def get_result(self):
        if "\n" in self.result:
            return "\n" + indent(self.result, stops=2)
        else:
            return self.result


# Setup {{{1
# Test fixture {{{2
# initialize {{{3
@pytest.fixture(scope="session")
def initialize():
    with cd(tests_dir):
        rm("configs .config .local repositories".split())
        cp("CONFIGS", "configs")
        mkdir(".config repositories .local".split())
        ln("~/.local/bin", ".local/bin")
        ln("~/.local/lib", ".local/lib")
        os.environ["HOME"] = str(cwd())

# initialize_configs {{{3
@pytest.fixture(scope="session")
def initialize_configs(initialize):
    with cd(tests_dir):
        cp("CONFIGS", ".config/emborg")
        for p in lsf(".config/emborg"):
            contents = p.read_text()
            contents = contents.replace('«TESTS»', tests_dir)
            p.write_text(contents)
        touch(".config/.nobackup")


# Tests {{{1
# test_emborg_without_configs{{{2
@parametrize(
    path = f'{tests_dir}/test-cases.nt',
    key = 'emborg without configs',
    schema = emborg_schema
)
def test_emborg_without_configs(
    initialize, opts, args, expected, expected_re, cmp_dirs, rm
):
    with cd(tests_dir):
        tester = EmborgTester(opts, args, expected, expected_re, cmp_dirs, rm)
        passes = tester.run()
        if not passes:
            result = dict(passes=passes, output=tester.get_result())
            expected = dict(passes=True, output=tester.get_expected())
            assert result == expected

# test_emborg_with_configs{{{2
@parametrize(
    path = f'{tests_dir}/test-cases.nt',
    key = 'emborg with configs',
    schema = emborg_schema
)
def test_emborg_with_configs(
    initialize_configs, opts, args, expected, expected_re, cmp_dirs, rm
):
    with cd(tests_dir):
        tester = EmborgTester(opts, args, expected, expected_re, cmp_dirs, rm)
        passes = tester.run()
        if not passes:
            result = dict(passes=passes, output=tester.get_result())
            expected = dict(passes=True, output=tester.get_expected())
            assert result == expected

# test_emborg_overdue {{{2
@parametrize(
    path = f'{tests_dir}/test-cases.nt',
    key = 'emborg-overdue',
    schema = emborg_overdue_schema
)
def test_emborg_overdue(initialize, conf, args, expected):
    with cd(tests_dir):
        if conf:
            with open('.config/overdue.conf', 'w') as f:
                f.write(conf)
        try:
            args = args.split() if is_str(args) else args
            overdue = Run(emborg_overdue_exe + args, "sOEW")
            assert overdue.stdout == expected
        except Error as e:
            return str(e) == expected
