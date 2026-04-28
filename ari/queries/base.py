"""Step-based workflow refactoring module.

This module contains the base classes and dataclasses for step-based workflows:
- Table: Enum for database tables (PROJECT, CALC)
- Requirement: Dataclass for step inputs
- Product: Dataclass for step outputs
- Step: Abstract base class for workflow steps
- StepRunner: Executes steps with validation and dependency management
"""

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any
from enum import Enum

# Re-export Table from database module
from ari.db.database import Table
from ari.db.database import Database


@dataclass
class Requirement:
    """Represents a required input for a Step.

    Attributes:
        key: The context key where the required data is stored
        source: The Table (PROJECT or CALC) where the data comes from
    """

    key: str
    source: Table


@dataclass
class Product:
    """Represents an output produced by a Step.

    Attributes:
        key: The context key where the produced data will be stored
        dest: The Table (PROJECT or CALC) where data is written
    """

    key: str
    dest: Table


class Step(ABC):
    """Abstract base class for workflow steps.

    Each step:
    - Has a unique name
    - Declares its requirements (inputs from context)
    - Declares its products (outputs to context)
    - Implements execute() to perform its logic

    The run() method orchestrates the step execution by populating ctx with
    data from db based on requires, calling execute(), and writing results
    back to db based on produces.
    """

    # Subclasses must define these class attributes
    name: str = ""
    requires: list[Requirement] = []
    produces: list[Product] = []

    def run(self, db: Database) -> None:
        """Orchestrate step execution.

        1. Populate ctx with data from db based on requires
        2. Call self.execute(db, ctx)
        3. Write products back to db based on produces

        Args:
            db: Database instance for reading/writing data
            ctx: Context dictionary with intermediate values
        """
        ctx: dict[str, Any] = {}

        # Populate ctx from db based on requirements
        for req in self.requires:
            ctx[req.key] = db.get(source=req.source, key=req.key)

        # Execute the step's logic
        self.execute(ctx)

        # Write products back to db
        for prod in self.produces:
            if prod.key not in ctx:
                raise ValueError(f"The item: {prod} is not added to the context! Either the Produces object is superfluous or the logic of the 'execute' method is not implemented correctly!")
            db.add(prod.dest, prod.key, ctx[prod.key])

    @abstractmethod
    def execute(self, ctx: dict[str, Any]) -> None:
        """Execute the step's logic.

        Args:
            db: Database instance for reading/writing data
            ctx: Context dictionary with intermediate values

        The execute method should:
        1. Read required data from ctx (already populated by run())
        2. Perform the step's logic
        3. Write results to ctx
        """
        ...


class StepRunner:
    """Executes steps with validation and dependency management.

    Responsibilities:
    - Validate step definitions
    - Sort steps topologically based on dependencies
    - Execute steps in order with shared context
    """

    def __init__(self, steps: list[Step]) -> None:
        """Initialize StepRunner with a list of Step classes.

        Args:
            steps: List of Step classes to execute
        """
        self.steps = steps

    def validate(self) -> None:
        """Validate step definitions for consistency.

        Checks:
        - All step names are unique
        - No circular dependencies exist
        - All requirement keys are either produced by a step or are root keys
        - No duplicate product keys across steps

        Raises:
            ValueError: If validation fails with descriptive message
        """
        # Build mappings from step classes
        step_names: dict[str, type[Step]] = {}
        product_keys: dict[
            str, type[Step]
        ] = {}  # Maps product key -> step that produces it

        # External PROJECT keys that are pre-populated, not produced by workflow steps.
        # These keys exist in the PROJECT sub-table but are provided externally
        # (e.g. colors from a GIS layer, cpts from a CPT file loader, soils from DB).
        # Validation allows duplicate product keys for these external inputs.
        external_project_keys: set[str] = {"colors", "cpts", "soils"}

        for step_class in self.steps:
            step_name = step_class.name

            # Check for duplicate step names
            if step_name in step_names:
                raise ValueError(
                    f"Duplicate step name: '{step_name}' found in "
                    f"{step_names[step_name].__name__} and {step_class.__name__}"
                )
            step_names[step_name] = step_class

            # Track product keys (skip external keys to allow duplicates)
            for prod in step_class.produces:
                if prod.key in external_project_keys:
                    # External key — skip tracking to allow duplicate declarations
                    continue
                if prod.key in product_keys:
                    raise ValueError(
                        f"Duplicate product key: '{prod.key}' produced by both "
                        f"{product_keys[prod.key].__name__} and {step_class.__name__}"
                    )
                product_keys[prod.key] = step_class

        # Check all requirements are satisfied
        for step_class in self.steps:
            for req in step_class.requires:
                if req.key in external_project_keys:
                    # External input - provided before workflow starts, skip check
                    continue
                if req.key not in product_keys:
                    raise ValueError(
                        f"Unsatisfied requirement: '{req.key}' required by "
                        f"{step_class.__name__} is not produced by any step"
                    )

        # Check for cycles using topological sort (Kahn's algorithm)
        # Build adjacency list: step_name -> list of step_names it depends on
        name_to_class: dict[str, type[Step]] = {
            step_class.name: step_class for step_class in self.steps
        }

        # Map product key -> step name that produces it
        product_to_step: dict[str, str] = {}
        for prod_key, step_class in product_keys.items():
            product_to_step[prod_key] = step_class.name

        # Build dependency graph: step_name -> [step_names it needs before]
        in_degree: dict[str, int] = {name: 0 for name in step_names}
        dependents: dict[str, list[str]] = {name: [] for name in step_names}

        for step_class in self.steps:
            step_name = step_class.name
            for req in step_class.requires:
                # Find which step produces this requirement
                producer_step = product_to_step.get(req.key)
                if producer_step and producer_step in step_names:
                    # producer_step must run before step_name
                    in_degree[step_name] += 1
                    dependents[producer_step].append(step_name)

        # Kahn's algorithm - if we can't process all nodes, there's a cycle
        queue = [name for name, degree in in_degree.items() if degree == 0]
        processed = 0

        while queue:
            current = queue.pop(0)
            processed += 1
            for dependent in dependents[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if processed != len(step_names):
            raise ValueError(
                "Cycle detected in step dependencies. "
                "Steps cannot be ordered topologically."
            )

    def run(self, db: Any) -> None:
        """Execute all steps in topological order.

        Args:
            db: Database instance

        Returns:
            Final context dictionary with all results

        Raises:
            ValueError: If validation fails (e.g., circular dependency)
        """
        # Validate workflow before execution
        self.validate()

        # Execute steps in provided order using step.run()
        # step.run() handles populate->execute->write per step
        for step in self.steps:
            step().run(db=db) # First instantiate step, then run it

