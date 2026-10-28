"""Runs every scenario in `features/` as a pytest test. Step definitions live in `conftest.py`."""
from pytest_bdd import scenarios

scenarios("features")
