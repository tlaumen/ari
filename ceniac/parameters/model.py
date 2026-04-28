from dataclasses import dataclass

@dataclass
class Color:
    soil: str
    color: str


@dataclass
class PileFoundationParams:
    """Parameters for a soil used in a pile foundation calculation"""

    soil: str
    K0: float
    gamma_nat: float  # natural volumetric weight
    gamma_sat: float  # saturated volumetric weight
    friction_angle: float  # drained friction angle
    compressible: bool  # if a material is relatively compressible, this is taken into account for the negative skin friction
    undrained_shear_strength: (
        float  # undrained shear strength, only relevant with compressible materials
    )
