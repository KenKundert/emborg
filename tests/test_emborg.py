# Test Emborg

# Imports {{{1
import os
import pytest
import re
import nestedtext as nt
from inform import is_str, Color, Error, indent
from shlib import Run, cd, cp, cwd, ln, lsf, mkdir, rm, set_prefs, touch
from textwrap import dedent


# Globals {{{1
# uses local code
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
parametrize = pytest.mark.parametrize


# EmborgTester class {{{1
class EmborgTester(object):
    def __init__(
        self,
        name,
        opts="",
        args="",
        config=None,
        expected=None,
        expected_re=None,
        cmp_dirs=None,
        rm=None,
    ):
        # expected == None implies that another test method is to be used if
        #     available, otherwise the run should not fail.
        # expected == FAILURE implies that the run should fail.
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

        self.name = name
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

    def get_result(self):
        if "\n" in self.result:
            return "\n" + indent(self.result, stops=2)
        else:
            return self.result


# Setup {{{1
# Load Tests {{{2
tests = nt.load(f'{tests_dir}/test-cases.nt')

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
# test_names {{{2
# assure all test names are unique
def test_names():
    names = set()
    for phase, tsts in tests.items():
        for name in tsts.keys():
            assert name not in names, f"Test name '{name}' is not unique."
            names.add(name)

# test_emborg_without_configs{{{2
@parametrize(
    'name, params',
    tests['emborg without configs'].items(),
    ids=tests['emborg without configs'].keys()
)
def test_emborg_without_configs(initialize, name, params):
    with cd(tests_dir):
        tester = EmborgTester(name, **params)
        passes = tester.run()
        if not passes:
            result = dict(passes=passes, output=tester.get_result())
            expected = dict(passes=True, output=tester.get_expected())
            assert result == expected, f'Test {tester.name}'

# test_emborg_with_configs{{{2
@parametrize(
    "name, params",
    tests['emborg with configs'].items(),
    ids = tests['emborg with configs'].keys()
)
def test_emborg_with_configs(initialize_configs, name, params):
    with cd(tests_dir):
        tester = EmborgTester(name, **params)
        passes = tester.run()
        if not passes:
            result = dict(passes=passes, output=tester.get_result())
            expected = dict(passes=True, output=tester.get_expected())
            assert result == expected, f'Test {tester.name}'

# test_emborg_overdue {{{2
@parametrize(
    "name, params",
    list(tests['emborg-overdue'].items()),
    ids = tests['emborg-overdue'].keys()
)
def test_emborg_overdue(initialize, name, params):
    with cd(tests_dir):
        if 'conf' in params:
            with open('.config/overdue.conf', 'w') as f:
                f.write(params['conf'])
        try:
            args = params.get('args', [])
            args = args.split() if is_str(args) else args
            overdue = Run(emborg_overdue_exe + args, "sOEW")
            assert overdue.stdout == params['expected']
        except Error as e:
            return str(e) == params['expected']
