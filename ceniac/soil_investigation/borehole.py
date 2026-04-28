from dataclasses import dataclass
from pathlib import Path
from datetime import date

from pygef import read_bore


def load_boreholes_bro():
    """Loads borehole data from BRO"""
    pass



@dataclass(kw_only=True)
class Borehole:
    """Object to represent a borehole investigation performed"""

    id_: str
    date: date
    x: float
    y: float
    surface_level: float
    depth_bottom: float
    descriptions: list[str]

def load_borehole(file_path: Path) -> Borehole:
    """Loads BH data from a given file and returns a Borehole object."""
    file_path = Path(file_path)

    if file_path.suffix.lower() not in [".gef", ".xml"]:
        raise ValueError("File extension is not .gef or .xml")

    bh = read_bore(file_path)

    if bh.delivered_location is None:
        raise ValueError(
            f"The easting and northing of borehole: {bh.bro_id} cannot be parsed"
        )

    df = bh.data
    bottoms = df["lowerBoundary"].to_list()
    descriptions = [str(d) for d in df["geotechnicalSoilName"].to_list()]

    if len(bottoms) == 0 or len(descriptions) == 0:
        raise ValueError(
            f"{bh.bro_id}: One or more of the lists 'bottoms' or 'descriptions' are empty."
        )

    if len(bottoms) != len(set(bottoms)):
        no_dupl = len(bottoms) - len(set(bottoms))
        raise ValueError(
            f"Depth values are not unique for {bh.bro_id}, with {no_dupl} duplicates"
        )

    return Borehole(
        id_=bh.bro_id,
        date=bh.research_report_date,
        x=bh.delivered_location.x,
        y=bh.delivered_location.y,
        surface_level=bh.delivered_vertical_position_offset,
        depth_bottom=bottoms,
        descriptions=descriptions,
    )
