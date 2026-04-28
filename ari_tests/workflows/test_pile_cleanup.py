"""Tests to verify test_pile.py has no module-level side effects.

This test module verifies that:
1. Module-level imports don't include database manipulation imports
2. No module-level functions like `create_test_data()` or `remove_data()` exist
3. No module-level objects like `sand` or `clay` PileFoundationParams exist
4. Tests that need DB state use the `workflow_db` fixture
"""

import ast
import inspect
from pathlib import Path

import pytest


# Imports for use in tests
from ari_tests.workflows.calculate import test_pile  # noqa: F401


class TestModuleLevelCleanup:
    """Tests verifying no module-level side effects exist."""

    @pytest.fixture
    def test_pile_source(self) -> str:
        """Read the source code of test_pile.py."""
        source_path = Path(__file__).parent / "calculate" / "test_pile.py"
        return source_path.read_text()

    @pytest.fixture
    def test_pile_ast(self, test_pile_source) -> ast.Module:
        """Parse test_pile.py into an AST."""
        return ast.parse(test_pile_source)

    def test_no_shutil_import(self, test_pile_source):
        """Verify shutil is not imported at module level."""
        assert "import shutil" not in test_pile_source

    def test_no_initialize_db_import(self, test_pile_source):
        """Verify initialize_db is not imported at module level."""
        assert "initialize_db" not in test_pile_source

    def test_no_color_to_db_import(self, test_pile_source):
        """Verify color_to_db is not imported at module level."""
        assert "color_to_db" not in test_pile_source

    def test_no_dump_db_import(self, test_pile_source):
        """Verify dump_db is not imported at module level."""
        assert "dump_db" not in test_pile_source

    def test_no_cpt_to_db_import(self, test_pile_source):
        """Verify cpt_to_db is not imported at module level."""
        assert "cpt_to_db" not in test_pile_source

    def test_no_soil_profile_to_db_import(self, test_pile_source):
        """Verify soil_profile_to_db is not imported at module level."""
        assert "soil_profile_to_db" not in test_pile_source

    def test_no_params_to_db_import(self, test_pile_source):
        """Verify params_to_db is not imported at module level."""
        assert "params_to_db" not in test_pile_source

    def test_no_create_new_calculation_table_import(self, test_pile_source):
        """Verify create_new_calculation_table is not imported at module level."""
        assert "create_new_calculation_table" not in test_pile_source

    def test_no_module_level_sand_object(self, test_pile_source):
        """Verify 'sand' is not defined at module level."""
        tree = ast.parse(test_pile_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "sand":
                        pytest.fail("Module-level 'sand' object found")
        # Also check the string
        assert "sand = PileFoundationParams(" not in test_pile_source

    def test_no_module_level_clay_object(self, test_pile_source):
        """Verify 'clay' is not defined at module level."""
        tree = ast.parse(test_pile_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "clay":
                        pytest.fail("Module-level 'clay' object found")
        # Also check the string
        assert "clay = PileFoundationParams(" not in test_pile_source

    def test_no_create_test_data_function(self, test_pile_source):
        """Verify create_test_data() function is not defined."""
        tree = ast.parse(test_pile_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "create_test_data":
                pytest.fail("create_test_data() function found")
        assert "def create_test_data()" not in test_pile_source

    def test_no_remove_data_function(self, test_pile_source):
        """Verify remove_data() function is not defined."""
        tree = ast.parse(test_pile_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "remove_data":
                pytest.fail("remove_data() function found")
        assert "def remove_data()" not in test_pile_source

    def test_no_module_level_create_test_data_call(self, test_pile_source):
        """Verify create_test_data() is not called at module level."""
        tree = ast.parse(test_pile_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "create_test_data"
                ):
                    pytest.fail("create_test_data() called at module level")
        assert "create_test_data()" not in test_pile_source

    def test_no_module_level_remove_data_call(self, test_pile_source):
        """Verify remove_data() is not called at module level."""
        tree = ast.parse(test_pile_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "remove_data":
                    pytest.fail("remove_data() called at module level")
        assert "remove_data()" not in test_pile_source


class TestWorkflowDbFixtureUsage:
    """Tests verifying tests use the workflow_db fixture."""

    @pytest.fixture
    def test_pile_source(self) -> str:
        """Read the source code of test_pile.py."""
        source_path = Path(__file__).parent / "calculate" / "test_pile.py"
        return source_path.read_text()

    @pytest.fixture
    def test_pile_ast(self, test_pile_source) -> ast.Module:
        """Parse test_pile.py into an AST."""
        return ast.parse(test_pile_source)

    def test_combine_soil_profiles_cpts_uses_workflow_db(self, test_pile_source):
        """Verify test_combine_soil_profiles_cpts uses workflow_db fixture."""
        # Check the function signature contains 'workflow_db' parameter
        assert "def test_combine_soil_profiles_cpts(workflow_db" in test_pile_source

    def test_combine_soil_profiles_cpts_error_cpt_uses_workflow_db(
        self, test_pile_source
    ):
        """Verify test_combine_soil_profiles_cpts_error_cpt uses workflow_db fixture."""
        assert (
            "def test_combine_soil_profiles_cpts_error_cpt(workflow_db"
            in test_pile_source
        )

    def test_combine_soil_profiles_cpts_error_soil_profile_uses_workflow_db(
        self, test_pile_source
    ):
        """Verify test_combine_soil_profiles_cpts_error_soil_profile uses workflow_db fixture."""
        assert (
            "def test_combine_soil_profiles_cpts_error_soil_profile(workflow_db"
            in test_pile_source
        )
