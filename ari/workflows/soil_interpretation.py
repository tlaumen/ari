from pathlib import Path
from typing import Callable
import re
import colorsys
import random

from geolib.soils import soil
from matplotlib.colors import rgb2hex
from rapidfuzz.distance import Levenshtein
from prompt_toolkit.filters import is_done
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import prompt

from ceniac.soil_investigation.cpt import load_cpt
from ceniac.soil_investigation.cpt import Cpt
from ceniac.soil_investigation.interpret import naive_qc_rf, run_interpreter
from ceniac.parameters.model import Color
from ceniac.soil_profile.soil_profile import SoilProfile
from ari.db.db import get_all_cpts, write_calc_data, get_calc_data
from ari.db.database import Table
from ari.db.db import db

CPT_FILE_EXTENSIONS = (".xml", ".XML", ".gef", ".GEF")
INTERPRETATION_NAME_MAP = {"Qc Rf interpretatie": naive_qc_rf}

CPT_NAME_KEY = "cpt"
SI_FOLDER_KEY = "folder-grondonderzoek"
CPT_INTERPRETATION_METHOD_KEY = "interpretatie-methode-cpt"


def query_cpt():
    # 0. Get top level folder si data
    top_level_folder = get_calc_data(key=SI_FOLDER_KEY)

    # 1. Get the cpt name
    cpt_name = prompt("Welke cpt wil je interpreteren?")

    # If file extension is included in the name, remove
    if cpt_name[:-4] in CPT_FILE_EXTENSIONS:
        cpt_name = cpt_name[:-4]

    # TODO: add further input validation, e.g. name cannot be empty, ...

    # 1. Load cpt data
    _cpt_path: Path | list[Path] = find_cpt(
        name=cpt_name, top_level_folder=top_level_folder
    )

    # 2. Choose cpt with user input in case of multiple values
    if isinstance(_cpt_path, list):
        cpt_path: Path = choose_cpt(_cpt_path)
    else:
        cpt_path = _cpt_path
    # The cpt name might have contained typo's extract actual file name from selection
    cpt_name = cpt_path.stem

    # 3. Load cpt
    cpt = load_cpt(cpt_path)

    # Assess if cpt name (of file) and cpt id are the same, if not, notify user
    if cpt.id_ != cpt_name:
        print(
            f"The cpt name: {cpt_name} and the id of the saved cpt: {cpt.id_} are not the same. Please note the cpt is referred to by the filename!"
        )

    # 4. Write data to database
    write_calc_data(key=CPT_NAME_KEY, data=cpt.id_)
    db.add(Table.PROJECT, "cpts", cpt)


def query_si_folder():
    # 2. Get folder to find file
    folder = prompt(f"Wat is de projectfolder? [Standaard: {Path.cwd()}]")
    if folder == "":
        top_level_folder = Path.cwd()
    else:
        n_attempts = 0
        top_level_folder = Path(folder)
        while not top_level_folder.exists():
            folder = prompt(
                f"De opgegeven folder bestaat niet. Wat is de projectfolder? [Standaard: {Path.cwd()}]"
            )
            top_level_folder = Path(folder)

            # Break with too many attempts
            n_attempts += 1
            if n_attempts == 5:
                raise ValueError(
                    "The folder you are entering does not exist. You performed 5 attempts and it still did not work.\nMost likely, something else is going wrong!"
                )

    write_calc_data(key=SI_FOLDER_KEY, data=top_level_folder)


def query_cpt_interpretation_method():
    # 3. Select interpretation function
    interpretation_function = choice(
        message="Welke cpt interpretatie methode wil je gebruiken?",
        options=[
            (function, name) for name, function in INTERPRETATION_NAME_MAP.items()
        ],
    )
    write_calc_data(key=CPT_INTERPRETATION_METHOD_KEY, data=interpretation_function)


def query_interpret_cpt():

    # Get cpt data
    cpt_name = get_calc_data(CPT_NAME_KEY)
    cpts = get_all_cpts()
    if not cpt_name in cpts:
        raise ValueError(
            f"Something has gone wrong! For unknown reason, your cpt name: {cpt_name} is not in the DB with cpts: {cpts}"
        )
    cpt = cpts[cpt_name]

    # Get interpretation function
    interpretation_function = get_calc_data(CPT_INTERPRETATION_METHOD_KEY)

    # Run interpretation workflow
    soil_profile = interpret_cpt(
        cpt=cpt, interpretation_function=interpretation_function
    )

    # Save soil profile
    soil_profile.based_on = cpt_name
    db.add(Table.PROJECT, "soilprofiles", soil_profile)


def interpret_cpt(
    cpt: Cpt, interpretation_function: Callable[[Cpt, float | int], SoilProfile]
) -> SoilProfile:
    """
    Contains workflow to obtain a soil profile from soil investigation.
    Initially only supports cpt's
    """

    # 2. Interpret cpt
    soil_profile = interpretation_function(cpt, 0.5)

    # 3. Manual check by human
    _soils = list(set(soil_profile.soils))
    soil_profile = run_interpreter(
        cpt=cpt, interpretation=soil_profile, soil_colors=_create_colors(_soils)
    )

    soil_profile = (
        soil_profile._fill()
    )  # TODO: THIS SHOULD DEFINITELY BE REMOVED/IMPROVED TOWARDS THE FUTURE!

    return soil_profile


def find_cpt(name: str, top_level_folder: Path) -> Path | list[Path]:
    """
    Get cpt with path walk relative to top level folder.
    If exact name is found, it is returned.
    If not approximately equal names are returned in a list, based on Levenshtein distance <= 2.
    """
    if not top_level_folder.exists():
        raise ValueError(f"The folder: {top_level_folder} does not exist!")

    # Get all cpts 'under' top level folder
    cpt_paths: list[Path] = []
    for (
        dirpath,
        _,
        files,
    ) in top_level_folder.walk():  # .walk available from python 3.12
        for file in files:
            if (
                file.endswith(".gef")
                or file.endswith(".xml")
                or file.endswith(".GEF")
                or file.endswith(".XML")
            ):
                cpt_paths.append(dirpath / file)

    if len(cpt_paths) == 0:
        raise ValueError("Wrong top level folder")

    # Check if cpt with exact name is in there
    for cp in cpt_paths:
        if cp.stem == name:
            return cp
    else:
        print("Exact filename could not be found. Possible a typo is made.")

    # Filter paths based on Lehvenstein distance relative to name
    # Maximum 2 characters difference
    cpt_paths = [cp for cp in cpt_paths if Levenshtein.distance(cp.stem, name) <= 2]

    if len(cpt_paths) == 0:
        raise ValueError(
            "The cpt name (or a similar name) could not be found. Please check:\n\t-the top level folder is correct\n\t-the name contains typos"
        )
    return cpt_paths


def choose_cpt(cpt_paths: list[Path]) -> Path:
    """From multiple cpt's that are approximately the same, choose the right one with user input"""
    style = Style.from_dict(
        {
            "frame.border": "#ff4444",
            "selected-option": "bold",
            # ('noreverse' because the default toolbar style uses 'reverse')
            "bottom-toolbar": "#ffffff bg:#333333 noreverse",
        }
    )
    cpt_path = choice(
        message="Welke cpt bedoel je?",
        options=[(cp, cp.name) for cp in cpt_paths],
        style=style,
        bottom_toolbar=HTML(
            " Druk op <b>[Omhoog]</b>/<b>[Omlaag]</b> om te selecteren, <b>[Enter]</b> om te bevestigen."
        ),
        show_frame=~is_done,
    )
    return cpt_path


def _create_colors(soils: list[str]) -> dict[str, str]:
    color_map: dict[str, str] = {}

    s_min = 50
    s_max = 100
    l_min = 45
    l_max = 65
    for soil in soils:
        if _is_word_in_string(word="silt", text=soil) or _is_word_in_string(
            word="leem", text=soil
        ):
            h_min = 30
            h_max = 35
        elif _is_word_in_string(word="klei", text=soil):
            h_min = 100
            h_max = 140
        elif _is_word_in_string(word="zand", text=soil):
            l_min = 25
            h_min = 60
            h_max = 75
        elif _is_word_in_string(word="veen", text=soil):
            l_min = 10
            l_max = 40
            h_min = 15
            h_max = 30
        elif _is_word_in_string(word="grind", text=soil):
            h_min = 5
            h_max = 10
            s_min = 0
            s_max = 3
            l_min = 10
            l_max = 50
        else:  # choose random color
            h_min = 0
            h_max = 360

        rgb = colorsys.hls_to_rgb(
            h=random.randint(h_min, h_max) / 360,
            l=random.randint(l_min, l_max) / 100,
            s=random.randint(s_min, s_max) / 100,
        )
        color_map[soil] = rgb2hex(rgb)
    return [Color(soil=k, color=v) for k, v in color_map.items()]


def _is_word_in_string(word: str, text: str) -> bool:
    """
    Check if a word exists as a complete word in a string.
    The checking is not case sensitive.

    Args:
        word: The word to search for
        text: The string to search in
    Returns:
        bool: True if word is found as a complete word, False otherwise

    Examples:
        >>> is_word_in_string('clay', 'I found some clay')
        True
        >>> is_word_in_string('clay', 'The soil is clayey')
        False
        >>> is_word_in_string('clay', 'clay-like substance')
        True
    """
    # Use \b for word boundaries - matches position between word and non-word character
    pattern = r"\b" + re.escape(word) + r"\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def rgb_to_hex(rgb: tuple[int]) -> str:
    return "".join("%02X" % round(i * 255) for i in rgb)


SOIL_INTERPRETATION_QUERIES = [
    query_si_folder,
    query_cpt,
    query_cpt_interpretation_method,
    query_interpret_cpt,
]
