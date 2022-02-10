# Tesr Emborg
#
# These tests require BorgBackup to be available.  As such, they are not really
# suitable for public continuous integration services such as GitHub Actions.

# Imports {{{1
import arrow
import json
import nestedtext as nt
import os
from parametrize_from_file import parametrize
from functools import partial
import pytest
import re
from inform import is_str, Color, Error, indent
from shlib import Run, cd, cp, cwd, ln, lsf, mkdir, rm, set_prefs, to_path, touch
from textwrap import dedent
from voluptuous import Schema, Optional, Required, Any


# Adapt parametrize_for_file to read dictionary rather than list
def name_from_dict_keys(cases):
    return [{**v, 'name': k} for k,v in cases.items()]

parametrize = partial(parametrize, preprocess=name_from_dict_keys)


# Globals {{{1
# uses local versions of emborg (../bu) and emborg_overdue (../od)
emborg_exe = "../bu".split()
emborg_overdue_exe = "../od".split()
# uses installed code
#emborg_exe = "emborg".split()
#emborg_overdue_exe = "emborg-overdue".split()
set_prefs(use_inform=True)
tests_dir = to_path(__file__).parent
emborg_dir = str(tests_dir.parent)
emborg_dir_wo_slash = emborg_dir.strip('/')
    # remove the leading slashes, it will be added back in tests if needed

# schema for test cases {{{2
emborg_schema = Schema({
    Required('name'): str,
    Optional('args', default='<PASS>'): Any(str, list),
    Optional('expected', default=""): str,
    Optional('expected_type', default=""): str,
    Optional('cmp_dirs', default=""): str,
    Optional('remove', default=""): str,
    Optional('dependencies', default=""): str,
}, required=True)
emborg_overdue_schema = Schema({
    Required('name'): str,
    Optional('conf', default=""): str,
    Optional('args', default=[]): Any(str, list),
    Required('expected', default=""): str,
    Required('expected_type', default=""): str,
    Optional('dependencies', default=""): str,
}, required=True)

# missing dependencies {{{2
missing_dependencies = set(
    os.environ.get('MISSING_DEPENDENCIES', '').lower().split()
)
def skip_test(dependencies):
    return set(dependencies.lower().split()) & missing_dependencies


# EmborgTester class {{{1
class EmborgTester(object):
    # constructor {{{2
    def __init__(self, args, expected, expected_type, cmp_dirs, remove):
        # args are the arguments to the emborg command
        # If expected, stdout/stderr should match the given value
        # expected_type may contain keywords, 'regex', 'diff', 'error', and/or
        # 'ignore'
        # - if regex is given then expected is taken to be a regular expression
        #   otherwise the result much match expected verbatim
        # - if diff is given then emborg is expected to exit with an exit status of 1
        # - if error is given then emborg is expected to exit with an exit status of 2
        # - if ignore is given, stdout/stderr is not checked
        # cmp_dirs is a pair of directories that, if given, should match exactly
        # remove contains files or directories to be deleted before the test runs
        #
        # args, expected, and cmp_dirs may contain the literal text fragment: ⟪EMBORG⟫
        # that is replaced by the absolute path to the emborg directory: .../emborg

        # replace ⟪EMBORG⟫ and ⟪DATE⟫ macros
        date = arrow.now().format("YYYY-MM-DD")
        args = args.split() if is_str(args) else args
        args = [a.replace("⟪EMBORG⟫", emborg_dir_wo_slash) for a in args]
        args = [a.replace("⟪DATE⟫", date) for a in args]
        if expected is not None:
            expected = expected.replace("⟪EMBORG⟫", emborg_dir_wo_slash)
            expected = expected.replace("⟪DATE⟫", date)
        if cmp_dirs:
            cmp_dirs = cmp_dirs.replace("⟪EMBORG⟫", emborg_dir_wo_slash)
            cmp_dirs = cmp_dirs.replace("⟪DATE⟫", date)

        self.args = args
        self.expected = expected
        self.expected_type = expected_type.split()
        self.cmp_dirs = cmp_dirs.split() if is_str(cmp_dirs) else cmp_dirs
        self.cmd = emborg_exe + self.args
        self.command = " ".join(self.cmd)
        self.remove = remove
        self.diffout = None

    # run() {{{2
    def run(self):
        # remove requested files and directories
        if self.remove:
            rm(self.remove.split())
        if '<PASS>' in self.args:
            return True

        # run command
        emborg = Run(self.cmd, "sOMW*")
        self.result = dedent(Color.strip_colors(emborg.stdout)).strip("\n")

        # check stdout
        matches = True
        if 'ignore' not in self.expected_type:
            expected, result = self.expected, self.result
            if 'sort-lines' in self.expected_type:
                expected = '\n'.join(sorted(expected.splitlines()))
                result = '\n'.join(sorted(result.splitlines()))
            if 'regex' in self.expected_type:
                matches = bool(re.fullmatch(expected, result))
            else:
                matches = expected == result

        if matches and self.cmp_dirs:
            gen_dir, ref_dir = self.cmp_dirs
            #self.expected = ''
            try:
                diff = Run(["diff", "--recursive", gen_dir, ref_dir], "sOMW")
                self.result = diff.stdout
            except Error as e:
                self.result = e.stdout
                matches = False

        # check exit status
        self.exit_status = emborg.status
        self.expected_exit_status = 0
        if 'diff' in self.expected_type:
            self.expected_exit_status = 1
        if 'error' in self.expected_type:
            self.expected_exit_status = 2
        if self.exit_status != self.expected_exit_status:
            matches = False

        return matches

    # get_expected() {{{2
    def get_expected(self):
        if "\n" in self.expected:
            expected = "\n" + indent(self.expected, stops=2)
        else:
            expected = self.expected
        return dict(exit_status=self.expected_exit_status, output=expected)

    # get_result() {{{2
    def get_result(self):
        if "\n" in self.result:
            result = "\n" + indent(self.result, stops=2)
        else:
            result = self.result
        return dict(exit_status=self.exit_status, output=result)


# Setup {{{1
# Test fixture {{{2
# initialize {{{3
@pytest.fixture(scope="session")
def initialize():
    with cd(tests_dir):
        rm("configs .config .local repositories configs.symlink".split())
        cp("CONFIGS", "configs")
        mkdir(".config repositories .local".split())
        ln("~/.local/bin", ".local/bin")
        ln("~/.local/lib", ".local/lib")
        ln("configs", "configs.symlink")
        os.environ["HOME"] = str(cwd())


# initialize_configs {{{3
@pytest.fixture(scope="session")
def initialize_configs(initialize):
    with cd(tests_dir):
        cp("CONFIGS", ".config/emborg")
        rm(".config/emborg/subdir")
        for p in lsf(".config/emborg"):
            contents = p.read_text()
            contents = contents.replace('⟪EMBORG⟫', emborg_dir)
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
    initialize,
    name, args, expected, expected_type, cmp_dirs, remove, dependencies
):
    if skip_test(dependencies):
        return
    with cd(tests_dir):
        tester = EmborgTester(args, expected, expected_type, cmp_dirs, remove)
        passes = tester.run()
        if not passes:
            result = tester.get_result()
            expected = tester.get_expected()
            assert result == expected, name
            raise AssertionError('test code failure')

# test_emborg_with_configs{{{2
@parametrize(
    path = f'{tests_dir}/test-cases.nt',
    key = 'emborg with configs',
    schema = emborg_schema
)
def test_emborg_with_configs(
    initialize_configs,
    name, args, expected, expected_type, cmp_dirs, remove, dependencies
):
    if skip_test(dependencies):
        return
    with cd(tests_dir):
        tester = EmborgTester(args, expected, expected_type, cmp_dirs, remove)
        passes = tester.run()
        if not passes:
            result = tester.get_result()
            expected = tester.get_expected()
            assert result == expected, name
            raise AssertionError('test code failure')

# test_emborg_overdue {{{2
@parametrize(
    path = f'{tests_dir}/test-cases.nt',
    key = 'emborg-overdue',
    schema = emborg_overdue_schema
)
def test_emborg_overdue(
    initialize,
    name, conf, args, expected, expected_type, dependencies
):
    if skip_test(dependencies):
        return
    with cd(tests_dir):
        if conf:
            with open('.config/overdue.conf', 'w') as f:
                f.write(conf)
        try:
            args = args.split() if is_str(args) else args
            overdue = Run(emborg_overdue_exe + args, "sOEW")
            if 'regex' in expected_type.split():
                assert bool(re.fullmatch(expected, overdue.stdout)), name
            else:
                assert expected == overdue.stdout, name
        except Error as e:
            assert str(e) == expected, name


# test_emborg_api {{{2
def test_emborg_api(initialize):
    with cd(tests_dir):
        from emborg import Emborg

        with Emborg('tests') as emborg:
            configs = emborg.configs
        assert configs == 'test0 test1 test2 test3'.split()

        for config in configs:
            # get the name of latest archive
            with Emborg(config) as emborg:
                borg = emborg.run_borg(
                    cmd = 'list',
                    args = ['--json', emborg.destination()]
                )
                response = json.loads(borg.stdout)
                print(response)
                archive = response['archives'][-1]['archive']

                # list files in latest archive
                borg = emborg.run_borg(
                    cmd = 'list',
                    args = ['--json-lines', emborg.destination(archive)]
                )
                json_data = '[' + ','.join(borg.stdout.splitlines()) + ']'
                response = json.loads(json_data)
                paths = sorted([entry['path'] for entry in response])
                for each in [
                    '⟪EMBORG⟫/tests/configs',
                    '⟪EMBORG⟫/tests/configs/README',
                    '⟪EMBORG⟫/tests/configs/overdue.conf',
                    '⟪EMBORG⟫/tests/configs/settings',
                    '⟪EMBORG⟫/tests/configs/subdir',
                    '⟪EMBORG⟫/tests/configs/subdir/file',
                    '⟪EMBORG⟫/tests/configs/test0',
                    '⟪EMBORG⟫/tests/configs/test1',
                    '⟪EMBORG⟫/tests/configs/test2',
                    '⟪EMBORG⟫/tests/configs/test2excludes',
                    '⟪EMBORG⟫/tests/configs/test2passphrase',
                    '⟪EMBORG⟫/tests/configs/test3',
                    '⟪EMBORG⟫/tests/configs/test4',
                    '⟪EMBORG⟫/tests/configs/test5',
                    '⟪EMBORG⟫/tests/configs/test6',
                    '⟪EMBORG⟫/tests/configs/test6patterns',
                    '⟪EMBORG⟫/tests/configs/test7',
                    '⟪EMBORG⟫/tests/configs/test7patterns',
                    '⟪EMBORG⟫/tests/configs/test8',
                ]:
                    each = each.replace("⟪EMBORG⟫", emborg_dir_wo_slash)
                    assert each in paths

