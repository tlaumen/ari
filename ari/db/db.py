from typing import Any
from pathlib import Path
from datetime import datetime
import pickle
from prompt_toolkit import print_formatted_text

from baml_client.types import Berekening

from ceniac.soil_investigation.cpt import Cpt
from ceniac.soil_profile.soil_profile import SoilProfile

from ari.db.database import ProjectTable, CalcTable, Database, Table


# Module-level database singleton
db = Database()


def initialize_db(path: Path | None = None):
    # If path is not specified, use current working directory user
    if path is None:
        path = Path.cwd()

    # Set the db singleton's dump path
    db._dump_path = path / ".ceniac"

    # If the database does not exist, create the folder
    db._dump_path.mkdir(parents=True, exist_ok=True)


def create_new_calculation_table(calc_type: Berekening):
    """Creates a new calculation session in the database."""
    session_id = db.calc.create_session(calc_type)
    dump_path = db._dump_path / str(session_id)
    if dump_path.exists():
        raise ValueError(f"Session dump folder already exists: {dump_path}")
    dump_path.mkdir(parents=True, exist_ok=True)


def color_to_db(soil: str, color: str):
    if soil in db.project.colors:
        raise ValueError(
            f"The color of soil: {soil} are already present in the 'colors' database table"
        )
    db.project.colors[soil] = color


def get_all_cpts() -> dict[str, Cpt]:
    return db.project.cpts


def get_all_soil_profiles() -> list[SoilProfile]:
    return list(db.project.soilprofiles.values())


def get_all_params() -> list[Any]:
    return db.project.params


def get_all_colors() -> dict[str, str]:
    return db.project.colors


def dump_db():
    """Dump the database to disk via the db singleton."""
    db.dump()


def load_db(path: Path):
    """Load the database from disk via the db singleton."""
    db.load(path)


def get_calc_folder() -> Path:
    """Gets the absolute path where the calculation currently performed is executed"""
    return db.calc_folder


def write_calc_data(key: str, data: Any):
    """Writes generic calculation data."""
    if db.calc.current_session and key in db.calc.current_session.data:
        print_formatted_text(
            "Doe voorzichtig! Je bent op dit moment bestaande opgeslagen data aan het overschrijven"
        )
    if isinstance(data, Cpt):
        raise ValueError(
            "It is not allowed to upload a Cpt object in the calc data. This should be uploaded through 'db.add(Table.PROJECT, \"cpts\", ...)'"
        )
    if isinstance(data, SoilProfile):
        raise ValueError(
            "It is not allowed to upload a SoilProfile object in the calc data. This should be uploaded through 'db.add(Table.PROJECT, \"soilprofiles\", ...)'"
        )
    db.calc.set_calc(key, data)


def get_calc_data(key: str) -> Any:
    """Get generic calculation data saved in the current session"""
    return db.calc.get_calc(key)
