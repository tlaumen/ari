from dataclasses import dataclass
from enum import IntFlag
from pathlib import Path
from collections import Counter
from pathlib import Path

import numpy as np
from pygef import read_cpt
import matplotlib.pyplot as plt


def load_cpts_bro():
    """Loads cpt xml format from BRO"""
    pass


@dataclass(kw_only=True)
class Cpt:
    """Dataclass representing all data measured with a cpt"""

    """
    [What role/responsibility this class has in the system]
    
    [Optional: Extended description of the problem it solves, key behaviors,
    design considerations, or performance characteristics]
    
    Parameters
    ----------
    init_param1
        What this controls. Guidance on typical values or ranges.
    init_param2
        What this affects. Interdependencies with other parameters.
    
    Attributes
    ----------
    public_attr1 : Type
        What this tracks. When/how it changes. Initial value if not obvious.
    public_attr2 : Type
        What this represents. How users should interpret it.
    
    Examples
    --------
    >>> # Typical initialization and basic usage
    >>> obj = ClassName(param1, param2)
    >>> result = obj.main_method()
    
    Notes
    -----
    - Thread-safety considerations
    - Lifecycle/cleanup requirements
    - Design patterns or architecture notes
    
    See Also
    --------
    RelatedClass : Brief relationship note
    """
    id_: str
    x: float  # x coordinate in RD system
    y: float  # y coordinate in RD system
    surface_level: float  # m+NAP
    predrill_depth: float  # m
    a_cone: float
    depths: np.ndarray  # m - surface level
    qc: np.ndarray  # MPa
    fs: np.ndarray  # kPa
    u2: np.ndarray | None = None

    @property
    def fr(self) -> np.ndarray:
        """Friction ratio parameter, derived from the skin friction fs and the cone resistance qc"""
        return 100 * self.fs / self.qc

    @property
    def levels(self) -> np.ndarray:
        """Levels of all measurements, derived from the original ground level and the depth per cpt measurement"""
        return self.surface_level - self.depths

    @property
    def bottom(self) -> float:
        """Bottom level of the cpt measurements"""
        return self.levels[-1]

    def _get_idx_level(self, requested_level: float) -> int:
        """Gets the idx of a measurement in the cpt at a given level"""
        for idx, level in enumerate(self.levels):
            if level <= requested_level:
                return idx
        else:
            raise ValueError(
                "Something strange has gone wrong with selecting the top idx!"
            )

    def calculate_average_qc(self, top: float, bottom: float) -> float:
        """Calculates the average qc value over a given interval"""
        if top > self.surface_level:
            raise ValueError(
                "The top must be below or equal to the surface level of the cpt"
            )
        if bottom < self.bottom:
            raise ValueError(
                "The bottom must be above or equal to the bottom level of the cpt"
            )
        if top <= bottom:
            raise ValueError("The top level should be above the bottom level!")

        # Get the top idx
        idx_top = self._get_idx_level(top)

        # Get bottom idx
        idx_bottom = self._get_idx_level(bottom)

        return (
            sum(self.qc[idx_top:idx_bottom]) / (idx_bottom - idx_top)
        )  # TODO: assess if this works for edgecases --> top = surface, bottom = bottom of cpt


def load_cpt(path: Path | str) -> Cpt:
    """Loads cpt using pygef from file path"""

    if isinstance(path, str):
        path = Path(path)
    cpt = read_cpt(path)

    depth = cpt.data["depth"].to_numpy()
    qc = cpt.data["coneResistance"].to_numpy()
    fs = cpt.data["localFriction"].to_numpy()
    u2 = cpt.data["porePressureU2"].to_numpy() if "porePressureU2" in cpt.data else None

    # Give a warning if any of the lists 'depth', 'qc' or 'fs' is empty
    if depth is None or qc is None or fs is None:
        raise ValueError(
            f"{cpt.alias}: One or more of the lists 'depth', 'qc', or 'fs' are empty."
        )

    # Check if the measurements are unique
    if len(depth) != len(set(depth)):
        duplicates = {k: v for k, v in Counter(depth).items() if v > 1}

        raise ValueError(
            f"Depth values are not unique for {cpt.alias}, with duplicates: {duplicates}"
        )

    # Check if the cpt name is provided, else raise exception
    if cpt.alias is None:
        if cpt.bro_id is None:
            raise ValueError(f"The cpt name for file: {path} could not be parsed")
        else:
            id_ = cpt.bro_id
    else:
        id_ = cpt.alias
    # Check if the surface level is filled in, else raise exception
    if cpt.delivered_vertical_position_offset is None:
        raise ValueError(f"The surface level should be filled in for {cpt.alias}")

    return Cpt(
        id_=id_,
        x=cpt.delivered_location.x,
        y=cpt.delivered_location.y,
        surface_level=cpt.delivered_vertical_position_offset,
        predrill_depth=cpt.predrilled_depth,
        a_cone=cpt.cone_surface_quotient
        if cpt.cone_surface_quotient is not None
        else 0.8,
        depths=depth,
        qc=qc,
        fs=fs,
        u2=u2,
    )


def plot_cpt(
    cpt: Cpt, qc_max: float | None = None
) -> tuple[plt.Figure, plt.Axes, plt.Axes]:  # pyright: ignore , required for plt.XXX imports
    """Creates a matplotlib figure with 2 axes of a Cpt"""
    fig, (ax1, ax2) = plt.subplots(ncols=2, sharey=True, gridspec_kw={"wspace": 0})
    ax1.plot(cpt.qc, cpt.levels, color="k", label="qc [MPa]")
    ax1.set_xlabel("qc [MPa]")
    ax1.set_ylabel("hoogte [m+NAP]")
    ax1.grid()
    if not qc_max is None:
        ax1.set_xlim(left=0, right=min(np.max(cpt.qc), qc_max))
    else:
        ax1.set_xlim(left=0)
    ax2.plot(cpt.fr, cpt.levels, color="b", label="friction ratio [%]")
    ax2.set_xlabel("wrijvingsgetal [%]")
    ax2.grid()
    ax2.invert_xaxis()
    ax2.set_xlim(left=10, right=0)
    return fig, ax1, ax2
