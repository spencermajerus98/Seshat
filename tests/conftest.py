"""Shared pytest fixtures."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db  # noqa: E402


@pytest.fixture()
def conn(tmp_path):
    c = db.connect(str(tmp_path / "test.db"), "test-passphrase")
    yield c
    c.close()
