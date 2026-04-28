from pathlib import Path

from ceniac.soil_investigation.cpt import load_cpt
from ceniac.soil_profile.soil_profile import Layer
from ceniac.soil_profile.soil_profile import SoilProfile


cpt = load_cpt(
    Path(__file__).parent.parent / "tests" / "soil_investigation" / "CPT002.xml"
)
SURFACE_LEVEL = 0
BOTTOM_PROFILE = -10
# Soil layers matching paalfundering.yaml expectations (klei, veen, zand sorted alphabetically)
KLEI_LAYER = Layer(soil="klei", top=SURFACE_LEVEL, bottom=-3)
VEEN_LAYER = Layer(soil="veen", top=-3, bottom=-6)
ZAND_LAYER = Layer(soil="zand", top=-6, bottom=BOTTOM_PROFILE)

sp = SoilProfile(
    name="soil_profile_1",
    surface_level=SURFACE_LEVEL,
    layers=[KLEI_LAYER, VEEN_LAYER, ZAND_LAYER],
    bottom=BOTTOM_PROFILE,
)

DB_DUMP_FOLDER = Path(__file__).parent / "data"
DB_PATH = DB_DUMP_FOLDER / ".ceniac" / "db.pkl"
