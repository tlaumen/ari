"""Fixtures for Step testing.

Testing Strategy:
- Use real database via fresh_db fixture (consistent with codebase)
- Mock UI components (prompt, choice, confirm) via SequentialMock
- Mock GUI components (MapPointSelector, run_interpreter) via GUIMock
- Each test gets clean DB state via fixture teardown

Import fixtures from sibling directories:
- fresh_db: Clean DB singleton, proper teardown
- cpt, sp: Test data fixtures

Import mocks from fixtures:
- SequentialMock: Mock prompt/choice/confirm calls
- GUIMock: Mock GUI components
"""

# Re-export fixtures from parent test infrastructure
from ari_tests.db.conftest import fresh_db  # noqa: F401
from ari_tests.fixtures.workflow_mocks import SequentialMock, GUIMock  # noqa: F401

# Import data fixtures and expose them as pytest fixtures
from ari_tests.test_utils import cpt, sp, DB_DUMP_FOLDER  # noqa: F401
