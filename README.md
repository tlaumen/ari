# ari

> **Note:** ari is currently under active development. The API and core components are
> subject to change as the project evolves.

**ari** is a civil engineering workflow automation package that combines domain-specific
calculation libraries, structured data management, and LLM integration to streamline
engineering calculations and report generation.

Initially developed for geotechnical engineering, ari is designed as a workflow
framework extensible to all civil engineering disciplines.

## Why ari?

Civil engineering calculations are often interconnected — a soil investigation feeds into
a pile calculation, which feeds into a foundation report. Existing frameworks tend to
handle this as a rigid, predefined sequence. ari addresses this through:

- **Dynamic Workflow Routing** — Natural language input is classified to determine the
  appropriate calculation path, allowing flexible workflows that adapt to the task at hand
- **Domain-Specific Data Structures** — First-class support for civil engineering
  primitives like CPT data, soil profiles, borehole logs, and pile geometries — no
  wrangling generic structures into domain shapes
- **Integrated Data Persistence** — Project data (CPTs, soil profiles, soil parameters)
  and calculation sessions are managed in a structured database, eliminating ad-hoc
  file-based passing of data between steps

## Architecture

ari is organized into three main components:

### ari — Workflow Orchestration

The `ari` package handles application-level logic:

- **`ari/queries/`** — Step and StepRunner integration, workflow definitions, and query execution
- **`ari/db/`** — Database integration for project and calculation state
- **`ari/report/`** — LaTeX report generation
- **`ari/map_selector/`** — Interactive map interface for CPT visualization and location selection
- **`ari/classify_work.py`** — LLM-based work classification and task routing

### ceniac — Calculation Logic

The `ceniac` subpackage contains the civil engineering calculation logic:

- **`ceniac/soil_profile/`** — Soil profile and layer data structures
- **`ceniac/soil_investigation/`** — CPT data structures and interpretation logic
- **`ceniac/calculate/`** — Pile foundation calculation implementations
- **`ceniac/parameters/`** — Soil parameter models (K₀, γ, φ, cᵤ, etc.)

### baml_src — Prompt Definitions

`baml_src/` contains BAML prompt definitions for LLM integration. This is an internal
implementation layer managed separately from the application logic.

## Directory Structure

```
ari/
├── queries/             # Step/StepRunner implementation & workflow definitions
├── db/                  # Database (ProjectTable, CalcTable)
├── report/              # LaTeX report generation
└── map_selector/         # Map-based CPT selector

ceniac/
├── soil_profile/        # Soil profile & layer structures
├── soil_investigation/  # CPT & borehole data
├── calculate/           # Pile calculation logic
└── parameters/          # Soil parameter models

baml_src/                # LLM prompt definitions (internal)
```

## Key Components

### ceniac Subpackage

The `ceniac` subpackage provides the domain-specific data structures and calculation
logic. It is designed to be usable independently of the ari workflow layer.

**Data structures:**
- `Cpt` — Cone Penetration Test data (qc, fr, levels)
- `Borehole` — Borehole log data
- `SoilProfile` — Layered soil representation with surface/bottom levels
- `Layer` — Individual soil layer (soil type, top, bottom)
- `PileFoundationParams` — Soil parameters for pile calculations (K₀, γ, φ, cᵤ, compressibility)

**Calculations:**
- CPT interpretation (naive qc/Rf-based soil classification)
- Soil stress profiles (effective stress, excess pore pressure)
- Skin friction calculation (positive and negative)
- Pile bearing capacity (base resistance, skin friction, total capacity)

### Step / StepRunner System

The Step/StepRunner system is the core execution model for workflows in `ari/queries/`.

- **Step** — A single unit of work. Each Step defines what data it requires as input
  (`requires`) and what data it produces as output (`produces`).
- **StepRunner** — Orchestrates a sequence of Steps, managing data flow between them
  and handling database persistence at each step.

Steps are implemented as classes extending a base `Step` class. Each step declares its
inputs via `requires` (source table and key) and outputs via `produces` (destination
table and key). The StepRunner handles:

- Populating the execution context from the database based on `requires`
- Calling the step's `execute()` method with the populated context
- Writing step outputs back to the database based on `produces`

The `StepRunner.validate()` method ensures the workflow is well-formed:
- Unique step names
- All requirements are produced by some step (or are external inputs like `cpts`)
- No circular dependencies

### Database

The database manages two types of data:

- **ProjectTable** — Project-scoped data that persists across calculation sessions:
  CPTs, soil profiles, soil parameters, and display colors
- **CalcTable** — Per-calculation session data: inputs and outputs of individual
  calculation steps

Data is stored as pickle files in a `.ceniac/` directory local to the project.

## Workflow System

The workflow system in `ari/queries/` provides a framework for composing Steps into
reusable, validated engineering workflows. Workflows are defined as ordered lists of
Step classes and executed via the StepRunner.

### Defining a Workflow

A workflow is simply a list of Step classes in execution order:

```python
from ari.queries.base import StepRunner

# Compose steps into a workflow
SOIL_INTERPRETATION_STEPS: list[type[Step]] = [
    LoadCptStep,
    SelectLocationStep,
    InterpretSoilStep,
    VerifyInterpretationStep,  # May request human feedback
    GroupLayersStep,
]

# Create and execute
workflow = StepRunner(SOIL_INTERPRETATION_STEPS)
workflow.run(db)
```

### Creating Custom Steps

To create a custom Step:

1. **Define requirements and products:**
   ```python
   from ari.queries.base import Step, Requirement, Product, Table

   class MyCalculationStep(Step):
       name = "my_calculation"
       requires = [
           Requirement(key="input_data", source=Table.CALC),
       ]
       produces = [
           Product(key="output_data", dest=Table.CALC),
       ]
   ```

2. **Implement the execute method:**
   ```python
   def execute(self, ctx: dict[str, Any]) -> None:
       data = ctx["input_data"]
       
       # Integrate ceniac logic
       from ceniac.soil_investigation import interpret_cpt
       result = interpret_cpt(data)
       
       ctx["output_data"] = result
   ```

3. **Register the step in a workflow:**
   ```python
   MY_WORKFLOW = [
       ExistingStep,        # From existing workflow
       MyCalculationStep,    # Your custom step
       OutputStep,           # Continue chain
   ]
   ```

### Workflow Validation

When a workflow is executed, `StepRunner` validates:

- **All inputs satisfied** — Every `requires` key is either produced by an earlier step
  or is an external input (e.g., `cpts`, `colors`)
- **No cycles** — Steps can be topologically ordered based on their dependencies
- **Unique products** — Each step produces distinct keys (prevents accidental overwrites)

If validation fails, execution is halted with a descriptive error.

### Data Flow Example

Consider a simplified pile foundation workflow:

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   LoadCpt   │───▶│ InterpretSoil    │───▶│ DeriveParams    │
│  requires:  │    │  requires:        │    │  requires:      │
│  - cpts      │    │  - cpts          │    │  - interpretation│
│  produces:  │    │  - locations      │    │  - colors       │
│  - cpts      │    │  produces:       │    │  produces:      │
└─────────────┘    │  - interpretation │    │  - params       │
                   └──────────────────┘    └─────────────────┘
                                                     │
                      ┌──────────────────────────────┘
                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ CalculatePile    │───▶│ GenerateReport  │───▶│ ExportResults   │
│  requires:      │    │  requires:      │    │  requires:      │
│  - interpretation│    │  - params       │    │  - report       │
│  - params        │    │  - calculations │    │  produces:      │
│  - geometry     │    │  produces:      │    │  - export       │
│  produces:      │    │  - report       │    └─────────────────┘
│  - calculations │    └─────────────────┘
└─────────────────┘
```

Each step reads from the database, performs its logic, and writes results back —
enabling downstream steps to consume upstream outputs without tight coupling.

## Current Implementations

### PAALFUNDERING Workflow

The primary implemented workflow is **PAALFUNDERING** (pile foundation), covering:

- Soil interpretation from CPT data
- Soil parameter derivation
- Pile capacity calculation
- LaTeX report generation

### ceniac Subpackage

The `ceniac` subpackage is used directly for:

- `Cpt` data loading and interpretation
- Soil profile management
- Pile capacity calculation
- Soil parameter definition

### LLM Integration

LLM integration handles task routing and report generation:

- **Work Classification** (`ari/classify_work.py`) — Natural language input is
  classified to determine the appropriate workflow
- **Report Generation** — BAML prompts in `baml_src/report/` generate report sections
  from calculation data

## Roadmap

ari is actively under development. Planned improvements include:

### LLM-Powered Document Parsing

Extracting structured data from engineering documents and drawings using LLM functions.

### Additional Workflows

- **Settlement Calculations** — Consolidation settlement under structural loads
- **Geotechnical Stability** — Slope stability and retaining wall analysis

### Database Upgrade

Transitioning from pickle-based storage to SQLite for improved query capabilities and data integrity.

### Expanded Domain Coverage

Extending beyond geotechnical engineering to other civil engineering disciplines.

## Contributing / Development

### Installation

Install dependencies with [uv](https://github.com/astral-sh/uv):

```bash
uv sync
```

### Testing

Tests are located in the `tests/` and `ari_tests/` directories. Evals for LLM prompts are
in `baml_src/`. Run all tests with pytest:

```bash
pytest
```

Markers are defined in `pyproject.toml`:
- `human` — Tests requiring human feedback
- `auto` — Tests that run automatically
- `ai` — Tests that execute LLM calls

### Pull Requests

Contributions are welcome. Please open a pull request with a clear description of the
changes and ensure all tests pass before submitting.
