"""
ari_tests/fixtures/workflow_mocks.py

Step 1: SequentialMock for prompt_toolkit (prompt, choice, confirm)
"""

from __future__ import annotations

import sys
from contextlib import ExitStack, contextmanager
from typing import Any, Iterator
from unittest.mock import MagicMock, patch


@contextmanager
def mock_llm_reports() -> Iterator[None]:
    """Context manager that patches all 6 BAML reporter methods.

    Patches b.FoundationDesign*Reporter methods on the sync_client singleton
    so that create_report() can run without real LLM calls.

    Yields None. Patches are applied only within the context; original methods
    are restored on exit.
    """
    from baml_client import sync_client

    b = sync_client.b

    reporters = {
        "FoundationDesignIntroductionReporter": "# 1. Introduction\nMock intro text.\n",
        "FoundationDesignSoilInvestigationReporter": "# 2. Soil investigation\nMock soil investigation text.\n[Tabel 1]\n",
        "FoundationDesignAssumptionsReporter": "# 3. Uitgangspunten\nMock assumptions text.\n[Tabel 2]\n",
        "FoundationDesignModellingReporter": "# 4. Modelling\nMock modelling text.\n[Tabel 3]\n[Tabel 4]\n",
        "FoundationDesignResultsReporter": "# 5. Results\nMock results text.\n[Tabel 5]\n[Figuur 1]\n",
        "FoundationDesignConclusionReporter": "# 6. Conclusion\nMock conclusion text.\n",
    }

    # Save originals (BamlSyncClient stores methods dynamically, so patch.object
    # cannot restore them automatically — we must do it manually)
    originals: dict[str, Any] = {}
    for method_name in reporters:
        originals[method_name] = getattr(b, method_name)

    def make_reporter(text: str):
        """Factory to capture text by value in a closure."""

        def reporter(*args: Any, **kwargs: Any) -> str:
            return text

        return reporter

    # Patch _llm_text_generation_router to reset model_input.elements before
    # each reporter call (to_llm_input() mutates elements in-place, breaking
    # the 2nd call on the same model_input instance)
    from ari.queries import pile_report as pile_report_module

    original_router = pile_report_module._llm_text_generation_router

    def patched_router(section_input: Any) -> str:
        # Reset elements so to_llm_input() always sees an empty list
        section_input.model_input.elements = []
        return original_router(section_input)

    try:
        # Apply patches to BAML reporters
        for method_name, text in reporters.items():
            setattr(b, method_name, make_reporter(text))
        # Apply patch to router
        pile_report_module._llm_text_generation_router = patched_router
        yield
    finally:
        # Restore originals
        for method_name, original in originals.items():
            setattr(b, method_name, original)
        pile_report_module._llm_text_generation_router = original_router


class SequentialMock:
    """Mock for prompt_toolkit calls (prompt, choice, confirm).

    Usage:
        seq = SequentialMock()
        seq.add_prompt("folder", "CPT002", "500")
        seq.add_choice(0)
        seq.add_confirm(True)

        with seq.mock():
            run_call_chain(call_chain)
    """

    def __init__(self) -> None:
        self._prompts: list[str] = []
        self._choices: list[int | str] = []
        self._confirms: list[bool] = []

    def add_prompt(self, *values: str) -> "SequentialMock":
        """Append values to the prompt queue."""
        self._prompts.extend(values)
        return self

    def add_choice(self, *values: int | str) -> "SequentialMock":
        """Append values to the choice queue."""
        self._choices.extend(values)
        return self

    def add_confirm(self, *values: bool) -> "SequentialMock":
        """Append values to the confirm queue."""
        self._confirms.extend(values)
        return self

    @contextmanager
    def mock(self) -> Iterator[None]:
        prompts_iter = iter(self._prompts)
        choices_iter = iter(self._choices)
        confirms_iter = iter(self._confirms)

        def mock_prompt(*args: Any, **kwargs: Any) -> str:
            try:
                return next(prompts_iter)
            except StopIteration:
                raise RuntimeError(
                    f"SequentialMock: prompts exhausted. Provided {len(self._prompts)}."
                )

        def mock_choice(*args: Any, **kwargs: Any) -> int | str:
            try:
                return next(choices_iter)
            except StopIteration:
                raise RuntimeError(
                    f"SequentialMock: choices exhausted. Provided {len(self._choices)}."
                )

        def mock_confirm(*args: Any, **kwargs: Any) -> bool:
            try:
                return next(confirms_iter)
            except StopIteration:
                raise RuntimeError(
                    f"SequentialMock: confirms exhausted. Provided {len(self._confirms)}."
                )

        # Always patch prompt_toolkit.shortcuts directly — this ensures the mock
        # applies even when called via real (non-imported) prompt_toolkit calls.
        # Also patch per-module bindings to handle "from X import Y" imports.
        modules = [
            "ari.workflows.soil_interpretation",
            "ari.workflows.calculate.pile",
            "ari.workflows.calculate.pile_calc_assumptions",
            "ari.workflows.derive_params",
            "ari.report.pile",
            "ari.queries.soil_interpretation",
            "ari.queries.derive_params",
            "ari.queries.pile_calc",
            "ari.queries.pile_report",
        ]
        with ExitStack() as stack:
            # Patch the source module directly (handles real prompt_toolkit calls)
            from prompt_toolkit import shortcuts

            stack.enter_context(patch.object(shortcuts, "prompt", mock_prompt))
            stack.enter_context(patch.object(shortcuts, "choice", mock_choice))
            stack.enter_context(patch.object(shortcuts, "confirm", mock_confirm))

            # Also patch per-module bindings (handles "from X import Y" imports)
            for mod in modules:
                if mod in sys.modules:
                    module = sys.modules[mod]
                    if hasattr(module, "prompt"):
                        stack.enter_context(patch(f"{mod}.prompt", mock_prompt))
                    if hasattr(module, "choice"):
                        stack.enter_context(patch(f"{mod}.choice", mock_choice))
                    if hasattr(module, "confirm"):
                        stack.enter_context(patch(f"{mod}.confirm", mock_confirm))
            yield


class GUIMock:
    """Mock for tkinter GUI functions.

    Usage:
        gui = GUIMock()
        gui.mock_location((155000, 463000))
        gui.mock_interpreter(my_soil_profile)

        with gui.mock():
            run_call_chain(call_chain)
    """

    def __init__(self) -> None:
        self._location: tuple[float, float] | None = None
        self._location_image: Any = None
        self._soil_profile: Any = None

    def mock_location(
        self,
        point: tuple[float, float] = (0, 0),
        top_view_image: Any = None,
    ) -> "GUIMock":
        """Configure the return value for query_pile_location.

        Args:
            point: (x, y) coordinates to return from get_point()
            top_view_image: Image to return from top_view_image property

        Returns:
            self for chaining
        """
        self._location = point
        self._location_image = top_view_image
        return self

    def mock_interpreter(self, soil_profile: Any) -> "GUIMock":
        """Configure the return value for run_interpreter.

        Args:
            soil_profile: SoilProfile to return, bypassing GUI

        Returns:
            self for chaining
        """
        self._soil_profile = soil_profile
        return self

    @contextmanager
    def mock(self) -> Iterator[None]:
        """Context manager that patches GUI functions.

        Patches:
        - pile_location_selector -> returns mock with configured point/image
        - run_interpreter -> returns configured soil_profile
        """
        with ExitStack() as stack:
            if self._location is not None:
                # Create closure to capture current location values
                def make_location_handler():
                    location = self._location
                    top_view_image = self._location_image

                    def handler(cpts: list) -> Any:
                        mock_selector = MagicMock()
                        mock_selector.get_point.return_value = location
                        mock_selector.top_view_image = top_view_image
                        return mock_selector

                    return handler

                stack.enter_context(
                    patch(
                        "ari.queries.pile_calc.pile_location_selector",
                        side_effect=make_location_handler(),
                    )
                )

            if self._soil_profile is not None:
                stack.enter_context(
                    patch(
                        "ari.queries.soil_interpretation.run_interpreter",
                        return_value=self._soil_profile,
                    )
                )

            yield
