# Project Context

## Package Manager
**Always use `uv` for all package management and running commands. Never use `pip`, `python`, `poetry`, or any other tool directly. Every python-related command must go through `uv`.**

Examples:
- Run a script: `uv run python script.py`
- Add a dependency: `uv add <package>`
- Run a tool: `uv run <tool>`

## Testing
Use `pytest` to run tests, always via `uv run pytest`.

### ⚠️ CRITICAL — Test Location Rules

**`tests/` contains ONLY unit tests for the ceniac subpackage. Nothing else. Do NOT add workflow tests, integration tests, or end-to-end tests here. If you are writing anything other than a ceniac unit test, it does NOT belong in `tests/`.**

**ALL workflow testing, integration testing, and end-to-end testing goes in `ari_tests/`. No exceptions.**

| Suite | Location | Command |
|---|---|---|
| ceniac unit tests only | `tests/` | `uv run pytest tests/` |
| ari subpackage + all workflow tests | `ari_tests/` | `uv run pytest ari_tests/` |

Always pass `-s` when running end-to-end tests or any tests marked with `@pytest.mark.human`.
