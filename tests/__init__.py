"""Test package initialiser — ensures ``src/`` is importable."""

import os
import sys

_SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# Re-export the helper so tests can do ``from tests.conftest import ...``
from tests.conftest import create_test_db  # noqa: F401, E402
