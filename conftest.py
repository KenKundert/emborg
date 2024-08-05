# Add missing dependency command line options to pytest command.

import os
import pytest
from inform import Error, Info as CmdLineOpts
from shlib import Run, set_prefs
set_prefs(use_inform=True)

# add command line options used to signal missing dependencies to pytest
def pytest_addoption(parser):
    # parser.addoption(
    #     "--borg-version", action="store", default="99.99.99", help="version number of borg"
    # )
    parser.addoption(
        "--no-fuse", action="store_true", default=None, help="fuse is not available"
    )

# process the command line options
@pytest.fixture(scope="session")
def dependency_options(request):
    options = CmdLineOpts()

    # run borg and determine its version number
    try:
        borg = Run(["borg", "--version"], modes="sOEW")
    except Error as e:
        e.report()
        raise SystemExit
    borg_version = borg.stdout
    borg_version = borg_version.split()[-1]
    borg_version = borg_version.partition('a')[0]  # strip off alpha version
    borg_version = borg_version.partition('b')[0]  # strip off beta version
    borg_version = borg_version.partition('rc')[0]  # strip off release candidate version
    borg_version = tuple(int(i) for i in borg_version.split('.'))
    options.borg_version = borg_version

    # determine whether FUSE is available
    # Can specify the --no-fuse command line option or set the
    # MISSING_DEPENDENCIES environment to 'fuse'.
    options.fuse_is_missing = request.config.getvalue("--no-fuse")
    if 'fuse' in os.environ.get('MISSING_DEPENDENCIES', '').lower().split():
        options.fuse_is_missing = True

    return options
