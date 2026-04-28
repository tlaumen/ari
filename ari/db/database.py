"""Database module with ProjectTable and CalcTable classes."""

from dataclasses import dataclass, field
from typing import Any
import copy
from pathlib import Path
from datetime import datetime
from enum import Enum
import pickle

from baml_client.types import Berekening

from ceniac.soil_investigation.cpt import Cpt
from ceniac.soil_profile.soil_profile import SoilProfile
from ceniac.parameters.model import PileFoundationParams
from ceniac.parameters.model import Color


@dataclass
class ProjectTable:
    """Project table storing CPTs and other project data."""

    cpts: list[Cpt] = field(default_factory=list)
    soilprofiles: list[SoilProfile] = field(default_factory=list)
    params: list[PileFoundationParams] = field(default_factory=list)
    colors: list[Color] = field(default_factory=list)
    
    # TODO: this method seems not to be used (or only in edge cases) -> refactor together with 'add' method on Database class
    def add(self, obj: Cpt | SoilProfile | PileFoundationParams | Color) -> None: # TODO: string now for colors -> should be object in future
        """Add an object to the appropriate sub-table based on its type.

        Raises TypeError if obj is of an unsupported type.
        """
        if isinstance(obj, Cpt):
            table = self.cpts
        elif isinstance(obj, SoilProfile):
            table = self.soilprofiles
        elif isinstance(obj, PileFoundationParams):
            table = self.params
        elif isinstance(obj, Color):
            table = self.colors
        else:
            raise TypeError(f"Unsupported type: {type(obj).__name__}")
        if obj in table:
            print("The object: {obj} is already in the table! BE CAREFULL THINGS ARE WORKING CORRECTLY!")
        table.append(obj)

@dataclass
class CalcTableEntry:
    """A single calculation session entry."""

    type: Berekening
    created: str
    data: dict[str, object]


@dataclass
class CalcTable:
    """Table for calculation sessions and session-scoped data."""

    sessions: dict[int, CalcTableEntry] = field(default_factory=dict)
    _current_session_id: int | None = None

    @property
    def current_session(self) -> CalcTableEntry | None:
        """Return the currently active session entry, or None."""
        return self.sessions.get(self._current_session_id)

    def create_session(self, calc_type: Berekening) -> int:
        """Create a new session and set it as current. Returns session ID."""
        id_ = max(self.sessions.keys(), default=-1) + 1
        self.sessions[id_] = CalcTableEntry(
            type=calc_type,
            created=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data={},
        )
        self._current_session_id = id_
        return id_

    def has(self, key: str) -> bool:
        """Return True if key exists in the current session's data."""
        return self.current_session is not None and key in self.current_session.data

    def set_calc(self, key: str, value: object) -> None:
        """Store a value under key in the current session."""
        if self.current_session is None:
            raise RuntimeError("No active session")
        self.current_session.data[key] = value

    def get_calc(self, key: str) -> object:
        """Retrieve a value by key from the current session."""
        if self.current_session is None:
            raise RuntimeError("No active session")
        if key not in self.current_session.data:
            raise KeyError(f"Key '{key}' not found")
        return self.current_session.data[key]

    def remove_calc(self, key: str) -> None:
        """Remove a key from the current session's data."""
        if self.current_session is None:
            raise RuntimeError("No active session")
        del self.current_session.data[key]


class Table(Enum):
    """Enum representing the two top-level database tables."""

    PROJECT = "project"
    CALC = "calc"


class Database:
    """Top-level database encapsulating project and calculation tables."""

    def __init__(self, path: Path | None = None, calc_type: Berekening | None = None):
        self.project = ProjectTable()
        self.calc = CalcTable()
        self._dump_path = path / ".ceniac" if path else Path.cwd() / ".ceniac"

        if calc_type is not None:
            self.calc.create_session(calc_type)

    def create_new_calculation(self, calc: Berekening) -> None:
        self.calc.create_session(calc)

    @property
    def calc_folder(self) -> Path:
        """Return the path to the current session's calculation folder."""
        if self.calc._current_session_id is None:
            raise ValueError("No active session")
        return self._dump_path / str(self.calc._current_session_id)

    def has(self, source: Table, key: str) -> bool:
        """Return True if key exists in the given table.

        For Table.PROJECT: returns True if key is a known sub-table name
            (cpts, soilprofiles, params, colors, soils).
        For Table.CALC: delegates to self.calc.has(key).
        """
        if source == Table.PROJECT:
            return key in {
                "cpts",
                "soilprofiles",
                "params",
                "colors",
            }
        else:
            return self.calc.has(key)

    def get(self, source: Table, key: str) -> Any:
        """Return a deep copy of the sub-table or session value for the given key.

        For Table.PROJECT: returns a copy.deepcopy of the sub-table
            (cpts, soilprofiles, params, colors, soils).
            The caller receives a fully independent copy — mutations do not affect
            the database. Raises KeyError if key is not a known sub-table name.
        For Table.CALC: delegates to self.calc.get_calc(key).
        """
        if source == Table.PROJECT:
            tables = {
                "cpts": self.project.cpts,
                "soilprofiles": self.project.soilprofiles,
                "params": self.project.params,
                "colors": self.project.colors,
            }
            if key not in tables:
                raise KeyError(f"Unknown sub-table: {key}")
            return copy.deepcopy(tables[key])
        else:
            return self.calc.get_calc(key)

    # TODO: this method should be refactored together with with 'add' method the ProjectTable class
    def add(self, source: Table, key: str, value: Any) -> None:
        """Add a value to the given table.

        For Table.PROJECT: routes to sub-table add or handles dict unpacking.
        For Table.CALC: delegates to calc.set_calc().

        Raises TypeError/ValueError from sub-methods as appropriate.
        """
        if source == Table.PROJECT:
            key_obj_map: dict[str, Cpt | SoilProfile | Color | PileFoundationParams] = {
                "cpts": Cpt,
                "soilprofiles": SoilProfile,
                "colors": Color,
                "params": PileFoundationParams
            }
            if key not in key_obj_map.keys():
                raise KeyError(f"Unknown sub-table: {key}")
            
            if isinstance(value, list):
                for obj in value:
                    if not isinstance(obj, key_obj_map[key]):
                        raise ValueError(f"The key of the db operation is: {key} but the obj is of type: {type(obj)}")
                    self.project.add(obj)
            else:
                if not isinstance(value, key_obj_map[key]):
                    raise ValueError(f"The key of the db operation is: {key} but the obj is of type: {type(value)}")
                self.project.add(value)
        else:
            self.calc.set_calc(key, value)

    def dump(self) -> None:
        """Serialize the full database state to a pickle file at _dump_path/db.pkl."""
        self._dump_path.mkdir(parents=True, exist_ok=True)
        path = self._dump_path / "db.pkl"
        data = {
            "project": {
                "cpts": self.project.cpts,
                "soilprofiles": self.project.soilprofiles,
                "params": self.project.params,
                "colors": self.project.colors,
            },
            "sessions": {
                id_: {"type": st.type, "created": st.created, "data": st.data}
                for id_, st in self.calc.sessions.items()
            },
            "_current_session_id": self.calc._current_session_id,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def load(self, path: Path) -> None:
        """Restore the database state from a pickle file produced by dump()."""
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.project.cpts = data["project"]["cpts"]
        self.project.soilprofiles = data["project"]["soilprofiles"]
        self.project.params = data["project"]["params"]
        self.project.colors = data["project"]["colors"]
        for id_, session_data in data["sessions"].items():
            self.calc.sessions[id_] = CalcTableEntry(**session_data)
        self.calc._current_session_id = data["_current_session_id"]
