# content of conftest.py

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--integtest", action="store_true", help="run integration tests"
    )
    parser.addoption(
        "--mpitest", action="store_true", help="run mpi tests"
    )


def pytest_runtest_setup(item):
    if 'integtest' in item.keywords and not item.config.getoption("--integtest"):
        pytest.skip("need --integtest option to run this test")
    if 'mpitest' in item.keywords and not item.config.getoption("--mpitest"):
        pytest.skip("need --mpitest option to run this test")
