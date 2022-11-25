"""
This module contains frequently used functions as well as instructions on how
to parse and process the raw data from different institutions
"""
import re
from typing import Dict, List, Optional

import icd10
import numpy as np
import pandas as pd
from dateutil.parser import parse


MRI_OR_CT_COL = "MRI/CT preoperativ (if both => take MRI)"
PATHOLOGY_COLS_POSITIVE = [
    "right Level Ia #positiv ",
    "right Level Ib #positiv",
    "right Level IIa #positiv",
    "right Level IIb #positiv",
    "right Level III #positiv",
    "right Level IV #positiv",
    "right Level Va #positiv",
    "right Level Vb #positiv",
    "left Level Ia #positiv",
    "left Level Ib #positiv",
    "left Level IIa #positiv",
    "left Level IIb #positiv",
    "left Level III #positiv",
    "left Level IV #positiv",
    "left Level Va #positiv",
    "left Level Vb #positiv",
]
PATHOLOGY_COLS_INVESTIGATED = [
    "right Level Ia #investigated ",
    "right Level Ib #investigated",
    "right Level IIa #investigated",
    "right Level IIb #investigated",
    "right Level III #investigated",
    "right Level IV #investigated",
    "right Level Va #investigated",
    "right Level Vb #investigated",
    "left Level Ia #investigated",
    "left Level Ib #investigated",
    "left Level IIa #investigated",
    "left Level IIb #investigated",
    "left Level III #investigated",
    "left Level IV #investigated",
    "left Level Va #investigated",
    "left Level Vb #investigated",
]

ALL_FALSE = [False] * 8
SUBLVL_PATTERN = {
    "left": {
        #      right side  Ia     Ib     IIa    IIb    III    IV     Va     Vb
        "I":  [*ALL_FALSE, True , True , False, False, False, False, False, False],
        "II": [*ALL_FALSE, False, False, True , True , False, False, False, False],
        "V":  [*ALL_FALSE, False, False, False, False, False, False, True , True ],
    },
    "right": {
        #      Ia     Ib     IIa    IIb    III    IV     Va     Vb     left side
        "I":  [True , True , False, False, False, False, False, False, *ALL_FALSE],
        "II": [False, False, True , True , False, False, False, False, *ALL_FALSE],
        "V":  [False, False, False, False, False, False, True , True , *ALL_FALSE],
    },
}


def smpl_date(entry):
    parsed_dt = parse(entry)
    return parsed_dt.strftime("%Y-%m-%d")


def smpl_diagnose(entry, *_args, **_kwargs):
    return {
        0: False,
        1: True,
        2: True,
    }[robust(int)(entry)]


def robust(func):
    """
    Wrapper that makes any type-conversion function 'robust' by simply returning
    `None` whenever any exception is thrown.
    """
    # pylint: disable=bare-except
    def wrapper(entry, *_args, **_kwargs):
        try:
            return func(entry)
        except:
            return None

    return wrapper


def get_subsite(entry, *_args, **_kwargs):
    """
    Get human-readable subsite from ICD-10 code.
    """
    match = re.search("(C[0-9]{2})(.[0-9]{1})?", entry)
    if match:
        for i in [0,1]:
            match_str = match.group(i)
            code = icd10.find(match_str)
            if code is not None and code.billable:
                return match_str
    return None


def map_to_lnl(entry, tumor_side, *_args, **_kwargs) -> Optional[List[str]]:
    """
    Map integers representing the location of the largest LN to the correct LNL.
    """
    res = []

    if entry is None or entry == "n/a" or pd.isna(entry):
        return None

    separator = re.compile(r"\s?\+\s?\/?\s?")
    locs = separator.split(entry)

    for loc in locs:
        div = int(loc) // 10
        mod = int(loc) % 10

        side = {1: "right", 2: "left"}[div]
        lnl = {1: "I", 2: "IIa", 3: "IIb", 4: "III", 5: "IV", 6: "V"}[mod]

        lat = "i" if side == map_side(tumor_side) else "c"

        res.append(f"{lat}-{lnl}")

    return "&".join(res)


def map_t_stage(clinical, pathological, *_args, **_kwargs):
    """
    Map their T-stage encoding to actual T-stages.
    """
    map_dict = {
        1: 1,
        2: 1,
        3: 2,
        4: 3,
        5: 4,
        6: 4,
    }
    try:
        return map_dict[robust(int)(clinical)]
    except KeyError:
        return None


def map_n_stage(entry, *_args, **_kwargs):
    """
    Map their N-stage encoding to actual N-stage.
    """
    try:
        return {
            0: 0,
            1: 1,
            2: 2,
            3: 2,
            4: 2,
            5: 2,
            6: 3
        }[robust(int)(entry)]
    except KeyError:
        return None


def map_location(entry, *_args, **_kwargs):
    """
    Map their location encoding to the semantic locations.
    """
    try:
        return {
            1: "oral cavity",
            2: "oropharynx",
            3: "hypopharynx",
            4: "larynx",
        }[robust(int)(entry)]
    except KeyError:
        return None


def map_side(entry, *_args, **_kwargs):
    """
    Map their side encoding to the semantic side.
    """
    try:
        return {
            1: "left",
            2: "right",
            3: "central",
        }[robust(int)(entry)]
    except KeyError:
        return None


def map_ct(entry, mri_or_ct, *_args, **_kwargs):
    """
    Call `robust(smpl_diagnose)` if the patient has a CT diagnose.
    """
    has_ct = robust(int)(mri_or_ct) == 2
    if not has_ct:
        return None
    return robust(smpl_diagnose)(entry)


def map_mri(entry, mri_or_ct, *_args, **_kwargs):
    """
    Call `robust(smpl_diagnose)` if the patient has an MRI diagnose.
    """
    has_mri = robust(int)(mri_or_ct) == 1
    if not has_mri:
        return None
    return robust(smpl_diagnose)(entry)


def _from_pathology(entry) -> Dict[str, int]:
    """
    Infer how many nodes in an LNL where investigated/positive per resection.
    """
    res = {}
    # If not available, leave empty
    if entry is None or entry == 'n/a' or pd.isna(entry):
        return res

    # split entry at '+' that may be surrounded by whitespace
    separator = re.compile(r"\s?\+\s?")
    marks = separator.split(entry)

    if marks is None or len(marks) == 0:
        return res

    # find numbers like '103b'
    pattern = re.compile("([0-9]{1,3})([a-z])?")

    # iterate through marks and check if they have been resected with other LNLs
    for mark in marks:
        match = pattern.search(mark)
        num = int(match.group(1)) % 100
        symbol = match.group(2) or "this"
        res[symbol] = num + res.get(symbol, 0)

    return res


def num_from_pathology(entry, *_args, **_kwargs) -> Optional[int]:
    """
    Infer number of involved nodes in LNL from pathology report.
    """
    res = _from_pathology(entry)

    if len(res) == 0:
        return None

    if res.get("this", 0) > 0:
        return res["this"]

    if all(num == 0 for num in res.values()):
        return 0

    return None


def binary_from_pathology(entry, *_args, **_kwargs) -> Optional[bool]:
    """
    Infer binary involvement from pathology report.
    """
    num = num_from_pathology(entry)

    if num is None:
        return None

    return num > 0


def num_super_from_pathology(*lnl_entries, lnl="I", side="left") -> Optional[int]:
    """
    Infer number of involved super LNLs (e.g. I, II and V) from pathology.
    """
    lnl_results = [_from_pathology(e) for e in lnl_entries]
    symbols = {s for lnl_res in lnl_results for s in lnl_res.keys() if s != "this"}

    known_lnl_invs = np.array([lnl_res.get("this") for lnl_res in lnl_results])
    try:
        res = sum(known_lnl_invs[SUBLVL_PATTERN[side][lnl]])
    except TypeError:
        res = None

    for symbol in symbols:
        symbol_nums = np.array([lnl_res.get(symbol,0) for lnl_res in lnl_results])
        symbol_pattern = symbol_nums > 0
        if all(symbol_pattern == SUBLVL_PATTERN[side][lnl]):
            res = (sum(symbol_nums[SUBLVL_PATTERN[side][lnl]]) / 2.) + (res or 0)

    return res


def binary_super_from_pathology(*lnl_entries, lnl="I", side="left") -> Optional[bool]:
    """
    Infer if super LNL is involved from pathology.
    """
    num = num_super_from_pathology(*lnl_entries, lnl=lnl, side=side)

    if num is None:
        return None

    return num > 0


def get_ct_date(entry, mri_or_ct, *_args, **_kwargs):
    """
    Determine the date of the CT diagnose.
    """
    has_ct = robust(int)(mri_or_ct) == 2
    if not has_ct:
        return None
    return robust(smpl_date)(entry)


def get_mri_date(entry, mri_or_ct, *_args, **_kwargs):
    """
    Determine the date of the MRI diagnose.
    """
    has_mri = robust(int)(mri_or_ct) == 1
    if not has_mri:
        return None
    return robust(smpl_date)(entry)


exclude = [
    ("Exclusion", lambda s: s == 1)
]


# dictionary indicating how to transform the columns
column_map = {
    # Patient information
    ('patient' , '#'    , 'id'             ): {"func": str, "columns": ["Local Study ID"]},
    ('patient' , '#'    , 'institution'    ): {"default": "Inselspital Bern"},
    ('patient' , '#'    , 'sex'            ): {"func": lambda x, *a, **k: "female" if x == 1 else "male", "columns": ["Gender"]},
    ('patient' , '#'    , 'age'            ): {"func": robust(int), "columns": ["Age diagnose"]},
    ('patient' , '#'    , 'diagnose_date'  ): {"func": robust(smpl_date), "columns": ["Date of diagnosis"]},
    ('patient' , '#'    , 'alcohol_abuse'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ["Alcohol"]},
    ('patient' , '#'    , 'nicotine_abuse' ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ["Smoking"]},
    ('patient' , '#'    , 'hpv_status'     ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ["p16"]},
    ('patient' , '#'    , 'neck_dissection'): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ["side of ND"]},
    ('patient' , '#'    , 'tnm_edition'    ): {"func": robust(int), "columns": ["TNM Edition"]},
    ('patient' , '#'    , 'n_stage'        ): {"func": map_n_stage, "columns": ["pN"]},
    ('patient' , '#'    , 'm_stage'        ): {"func": lambda x, *a, **k: 2 if x == 'x' else robust(int)(x), "columns": ["M-Stage"]},

    # Tumor information
    ('tumor'   , '1'    , 'location'       ): {"func": map_location, "columns": ["Primary Tumor"]},
    ('tumor'   , '1'    , 'subsite'        ): {"func": get_subsite, "columns": ["ICD-O-3 code"]},
    ('tumor'   , '1'    , 'side'           ): {"func": map_side, "columns": ["side"]},
    ('tumor'   , '1'    , 'central'        ): {"func": lambda x, *a, **k: True if robust(int)(x) == 3 else False, "columns": ["side"]},
    ('tumor'   , '1'    , 'extension'      ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ["Extension over the mid-sagital plane"]},
    ('tumor'   , '1'    , 'volume'         ): {"default": None},
    ('tumor'   , '1'    , 'stage_prefix'   ): {"default": "p"},
    ('tumor'   , '1'    , 't_stage'        ): {"func": map_t_stage, "columns": ["cT", "pT"]},

    # CT & MRI are displayed in the same table. A diagnose is considered MRI,
    # when available and CT only if MRI is not recorded (and CT available)
    ('CT'                , 'info'  , 'date'): {"func": get_ct_date, "columns": ["Date of preoperativ  CT Thorax", MRI_OR_CT_COL]},
    ('CT'                , 'left'  , 'I'   ): {"default": None},
    ('CT'                , 'left'  , 'Ia'  ): {"func": map_ct, "columns": ["left Level Ia", MRI_OR_CT_COL]},
    ('CT'                , 'left'  , 'Ib'  ): {"func": map_ct, "columns": ["left Level Ib", MRI_OR_CT_COL]},
    ('CT'                , 'left'  , 'II'  ): {"default": None},
    ('CT'                , 'left'  , 'IIa' ): {"func": map_ct, "columns": ["left Level IIa", MRI_OR_CT_COL]},
    ('CT'                , 'left'  , 'IIb' ): {"func": map_ct, "columns": ["left Level IIb", MRI_OR_CT_COL]},
    ('CT'                , 'left'  , 'III' ): {"func": map_ct, "columns": ["left Level III", MRI_OR_CT_COL]},
    ('CT'                , 'left'  , 'IV'  ): {"func": map_ct, "columns": ["left Level IV", MRI_OR_CT_COL]},
    ('CT'                , 'left'  , 'V'   ): {"default": None},
    ('CT'                , 'left'  , 'Va'  ): {"func": map_ct, "columns": ["left Level Va", MRI_OR_CT_COL]},
    ('CT'                , 'left'  , 'Vb'  ): {"func": map_ct, "columns": ["left Level Vb", MRI_OR_CT_COL]},
    ('CT'                , 'right' , 'I'   ): {"default": None},
    ('CT'                , 'right' , 'Ia'  ): {"func": map_ct, "columns": ["right Level Ia", MRI_OR_CT_COL]},
    ('CT'                , 'right' , 'Ib'  ): {"func": map_ct, "columns": ["right Level Ib", MRI_OR_CT_COL]},
    ('CT'                , 'right' , 'II'  ): {"default": None},
    ('CT'                , 'right' , 'IIa' ): {"func": map_ct, "columns": ["right Level IIa", MRI_OR_CT_COL]},
    ('CT'                , 'right' , 'IIb' ): {"func": map_ct, "columns": ["right Level IIb", MRI_OR_CT_COL]},
    ('CT'                , 'right' , 'III' ): {"func": map_ct, "columns": ["right Level III", MRI_OR_CT_COL]},
    ('CT'                , 'right' , 'IV'  ): {"func": map_ct, "columns": ["right Level IV", MRI_OR_CT_COL]},
    ('CT'                , 'right' , 'V'   ): {"default": None},
    ('CT'                , 'right' , 'Va'  ): {"func": map_ct, "columns": ["right Level Va", MRI_OR_CT_COL]},
    ('CT'                , 'right' , 'Vb'  ): {"func": map_ct, "columns": ["right Level Vb", MRI_OR_CT_COL]},

    # CT & MRI are displayed in the same table. A diagnose is considered MRI,
    # when available and CT only if MRI is not recorded (and CT available)
    ('MRI'               , 'info'  , 'date'): {"func": get_mri_date, "columns": ["Date of  preoperativ  MRI", MRI_OR_CT_COL]},
    ('MRI'               , 'left'  , 'I'   ): {"default": None},
    ('MRI'               , 'left'  , 'Ia'  ): {"func": map_mri, "columns": ["left Level Ia", MRI_OR_CT_COL]},
    ('MRI'               , 'left'  , 'Ib'  ): {"func": map_mri, "columns": ["left Level Ib", MRI_OR_CT_COL]},
    ('MRI'               , 'left'  , 'II'  ): {"default": None},
    ('MRI'               , 'left'  , 'IIa' ): {"func": map_mri, "columns": ["left Level IIa", MRI_OR_CT_COL]},
    ('MRI'               , 'left'  , 'IIb' ): {"func": map_mri, "columns": ["left Level IIb", MRI_OR_CT_COL]},
    ('MRI'               , 'left'  , 'III' ): {"func": map_mri, "columns": ["left Level III", MRI_OR_CT_COL]},
    ('MRI'               , 'left'  , 'IV'  ): {"func": map_mri, "columns": ["left Level IV", MRI_OR_CT_COL]},
    ('MRI'               , 'left'  , 'V'   ): {"default": None},
    ('MRI'               , 'left'  , 'Va'  ): {"func": map_mri, "columns": ["left Level Va", MRI_OR_CT_COL]},
    ('MRI'               , 'left'  , 'Vb'  ): {"func": map_mri, "columns": ["left Level Vb", MRI_OR_CT_COL]},
    ('MRI'               , 'right' , 'I'   ): {"default": None},
    ('MRI'               , 'right' , 'Ia'  ): {"func": map_mri, "columns": ["right Level Ia", MRI_OR_CT_COL]},
    ('MRI'               , 'right' , 'Ib'  ): {"func": map_mri, "columns": ["right Level Ib", MRI_OR_CT_COL]},
    ('MRI'               , 'right' , 'II'  ): {"default": None},
    ('MRI'               , 'right' , 'IIa' ): {"func": map_mri, "columns": ["right Level IIa", MRI_OR_CT_COL]},
    ('MRI'               , 'right' , 'IIb' ): {"func": map_mri, "columns": ["right Level IIb", MRI_OR_CT_COL]},
    ('MRI'               , 'right' , 'III' ): {"func": map_mri, "columns": ["right Level III", MRI_OR_CT_COL]},
    ('MRI'               , 'right' , 'IV'  ): {"func": map_mri, "columns": ["right Level IV", MRI_OR_CT_COL]},
    ('MRI'               , 'right' , 'V'   ): {"default": None},
    ('MRI'               , 'right' , 'Va'  ): {"func": map_mri, "columns": ["right Level Va", MRI_OR_CT_COL]},
    ('MRI'               , 'right' , 'Vb'  ): {"func": map_mri, "columns": ["right Level Vb", MRI_OR_CT_COL]},

    ('PET'               , 'info'  , 'date'): {"func": robust(smpl_date), "columns": ["Date of preoperativ PET-CT"]},
    ('PET'               , 'left'  , 'I'   ): {"default": None},
    ('PET'               , 'left'  , 'Ia'  ): {"func": robust(smpl_diagnose), "columns": ["left Level Ia.1"]},
    ('PET'               , 'left'  , 'Ib'  ): {"func": robust(smpl_diagnose), "columns": ["left Level Ib.1"]},
    ('PET'               , 'left'  , 'II'  ): {"default": None},
    ('PET'               , 'left'  , 'IIa' ): {"func": robust(smpl_diagnose), "columns": ["left Level IIa.1"]},
    ('PET'               , 'left'  , 'IIb' ): {"func": robust(smpl_diagnose), "columns": ["left Level IIb.1"]},
    ('PET'               , 'left'  , 'III' ): {"func": robust(smpl_diagnose), "columns": ["left Level III.1"]},
    ('PET'               , 'left'  , 'IV'  ): {"func": robust(smpl_diagnose), "columns": ["left Level IV.1"]},
    ('PET'               , 'left'  , 'V'   ): {"default": None},
    ('PET'               , 'left'  , 'Va'  ): {"func": robust(smpl_diagnose), "columns": ["left Level Va.1"]},
    ('PET'               , 'left'  , 'Vb'  ): {"func": robust(smpl_diagnose), "columns": ["left Level Vb.1"]},
    ('PET'               , 'right' , 'I'   ): {"default": None},
    ('PET'               , 'right' , 'Ia'  ): {"func": robust(smpl_diagnose), "columns": ["right Level Ia.1"]},
    ('PET'               , 'right' , 'Ib'  ): {"func": robust(smpl_diagnose), "columns": ["right Level Ib.1"]},
    ('PET'               , 'right' , 'II'  ): {"default": None},
    ('PET'               , 'right' , 'IIa' ): {"func": robust(smpl_diagnose), "columns": ["right Level IIa.1"]},
    ('PET'               , 'right' , 'IIb' ): {"func": robust(smpl_diagnose), "columns": ["right Level IIb.1"]},
    ('PET'               , 'right' , 'III' ): {"func": robust(smpl_diagnose), "columns": ["right Level III.1"]},
    ('PET'               , 'right' , 'IV'  ): {"func": robust(smpl_diagnose), "columns": ["right Level IV.1"]},
    ('PET'               , 'right' , 'V'   ): {"default": None},
    ('PET'               , 'right' , 'Va'  ): {"func": robust(smpl_diagnose), "columns": ["right Level Va.1"]},
    ('PET'               , 'right' , 'Vb'  ): {"func": robust(smpl_diagnose), "columns": ["right Level Vb.1"]},

    # pathology in boolean form
    ('pathology'         , 'info'  , 'date'): {"func": robust(smpl_date), "columns": ["Date of ND"]},
    ('pathology'         , 'left'  , 'I'   ): {"func": binary_super_from_pathology, "kwargs": {"lnl": "I", "side": "left"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('pathology'         , 'left'  , 'Ia'  ): {"func": binary_from_pathology, "columns": ["left Level Ia #positiv"]},
    ('pathology'         , 'left'  , 'Ib'  ): {"func": binary_from_pathology, "columns": ["left Level Ib #positiv"]},
    ('pathology'         , 'left'  , 'II'  ): {"func": binary_super_from_pathology, "kwargs": {"lnl": "II", "side": "left"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('pathology'         , 'left'  , 'IIa' ): {"func": binary_from_pathology, "columns": ["left Level IIa #positiv"]},
    ('pathology'         , 'left'  , 'IIb' ): {"func": binary_from_pathology, "columns": ["left Level IIb #positiv"]},
    ('pathology'         , 'left'  , 'III' ): {"func": binary_from_pathology, "columns": ["left Level III #positiv"]},
    ('pathology'         , 'left'  , 'IV'  ): {"func": binary_from_pathology, "columns": ["left Level IV #positiv"]},
    ('pathology'         , 'left'  , 'V'   ): {"func": binary_super_from_pathology, "kwargs": {"lnl": "V", "side": "left"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('pathology'         , 'left'  , 'Va'  ): {"func": binary_from_pathology, "columns": ["left Level Va #positiv"]},
    ('pathology'         , 'left'  , 'Vb'  ): {"func": binary_from_pathology, "columns": ["left Level Vb #positiv"]},
    ('pathology'         , 'right' , 'I'   ): {"func": binary_super_from_pathology, "kwargs": {"lnl": "I", "side": "right"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('pathology'         , 'right' , 'Ia'  ): {"func": binary_from_pathology, "columns": ["right Level Ia #positiv "]},
    ('pathology'         , 'right' , 'Ib'  ): {"func": binary_from_pathology, "columns": ["right Level Ib #positiv"]},
    ('pathology'         , 'right' , 'II'  ): {"func": binary_super_from_pathology, "kwargs": {"lnl": "II", "side": "right"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('pathology'         , 'right' , 'IIa' ): {"func": binary_from_pathology, "columns": ["right Level IIa #positiv"]},
    ('pathology'         , 'right' , 'IIb' ): {"func": binary_from_pathology, "columns": ["right Level IIb #positiv"]},
    ('pathology'         , 'right' , 'III' ): {"func": binary_from_pathology, "columns": ["right Level III #positiv"]},
    ('pathology'         , 'right' , 'IV'  ): {"func": binary_from_pathology, "columns": ["right Level IV #positiv"]},
    ('pathology'         , 'right' , 'V'   ): {"func": binary_super_from_pathology, "kwargs": {"lnl": "V", "side": "right"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('pathology'         , 'right' , 'Va'  ): {"func": binary_from_pathology, "columns": ["right Level Va #positiv"]},
    ('pathology'         , 'right' , 'Vb'  ): {"func": binary_from_pathology, "columns": ["right Level Vb #positiv"]},

    # # number of dissected nodes
    ('total_dissected'   , 'info'  , 'date'): {"func": robust(smpl_date), "columns": ["Date of ND"]},
    ('total_dissected'   , 'left'  , 'I'   ): {"func": num_super_from_pathology, "kwargs": {"lnl": "I", "side": "left"}, "columns": PATHOLOGY_COLS_INVESTIGATED},
    ('total_dissected'   , 'left'  , 'Ia'  ): {"func": num_from_pathology, "columns": ["left Level Ia #investigated"]},
    ('total_dissected'   , 'left'  , 'Ib'  ): {"func": num_from_pathology, "columns": ["left Level Ib #investigated"]},
    ('total_dissected'   , 'left'  , 'II'  ): {"func": num_super_from_pathology, "kwargs": {"lnl": "II", "side": "left"}, "columns": PATHOLOGY_COLS_INVESTIGATED},
    ('total_dissected'   , 'left'  , 'IIa' ): {"func": num_from_pathology, "columns": ["left Level IIa #investigated"]},
    ('total_dissected'   , 'left'  , 'IIb' ): {"func": num_from_pathology, "columns": ["left Level IIb #investigated"]},
    ('total_dissected'   , 'left'  , 'III' ): {"func": num_from_pathology, "columns": ["left Level III #investigated"]},
    ('total_dissected'   , 'left'  , 'IV'  ): {"func": num_from_pathology, "columns": ["left Level IV #investigated"]},
    ('total_dissected'   , 'left'  , 'V'   ): {"func": num_super_from_pathology, "kwargs": {"lnl": "V", "side": "left"}, "columns": PATHOLOGY_COLS_INVESTIGATED},
    ('total_dissected'   , 'left'  , 'Va'  ): {"func": num_from_pathology, "columns": ["left Level Va #investigated"]},
    ('total_dissected'   , 'left'  , 'Vb'  ): {"func": num_from_pathology, "columns": ["left Level Vb #investigated"]},
    ('total_dissected'   , 'right' , 'I'   ): {"func": num_super_from_pathology, "kwargs": {"lnl": "I", "side": "right"}, "columns": PATHOLOGY_COLS_INVESTIGATED},
    ('total_dissected'   , 'right' , 'Ia'  ): {"func": num_from_pathology, "columns": ["right Level Ia #investigated "]},
    ('total_dissected'   , 'right' , 'Ib'  ): {"func": num_from_pathology, "columns": ["right Level Ib #investigated"]},
    ('total_dissected'   , 'right' , 'II'  ): {"func": num_super_from_pathology, "kwargs": {"lnl": "II", "side": "right"}, "columns": PATHOLOGY_COLS_INVESTIGATED},
    ('total_dissected'   , 'right' , 'IIa' ): {"func": num_from_pathology, "columns": ["right Level IIa #investigated"]},
    ('total_dissected'   , 'right' , 'IIb' ): {"func": num_from_pathology, "columns": ["right Level IIb #investigated"]},
    ('total_dissected'   , 'right' , 'III' ): {"func": num_from_pathology, "columns": ["right Level III #investigated"]},
    ('total_dissected'   , 'right' , 'IV'  ): {"func": num_from_pathology, "columns": ["right Level IV #investigated"]},
    ('total_dissected'   , 'right' , 'V'   ): {"func": num_super_from_pathology, "kwargs": {"lnl": "V", "side": "right"}, "columns": PATHOLOGY_COLS_INVESTIGATED},
    ('total_dissected'   , 'right' , 'Va'  ): {"func": num_from_pathology, "columns": ["right Level Va #investigated"]},
    ('total_dissected'   , 'right' , 'Vb'  ): {"func": num_from_pathology, "columns": ["right Level Vb #investigated"]},

    # # Number of positive nodes
    ('total_positive'    , 'info'  , 'date'            ): {"func": robust(smpl_date), "columns": ["Date of ND"]},
    ('total_positive'    , 'info'  , 'largest_node_mm' ): {"func": robust(float), "columns": ["Size of largest LN (mm)"]},
    ('total_positive'    , 'info'  , 'largest_node_lnl'): {"func": map_to_lnl, "columns": ["location of largest LN", "side"]},
    ('total_positive'    , 'left'  , 'I'               ): {"func": num_super_from_pathology, "kwargs": {"lnl": "I", "side": "left"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('total_positive'    , 'left'  , 'Ia'              ): {"func": num_from_pathology, "columns": ["left Level Ia #positiv"]},
    ('total_positive'    , 'left'  , 'Ib'              ): {"func": num_from_pathology, "columns": ["left Level Ib #positiv"]},
    ('total_positive'    , 'left'  , 'II'              ): {"func": num_super_from_pathology, "kwargs": {"lnl": "II", "side": "left"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('total_positive'    , 'left'  , 'IIa'             ): {"func": num_from_pathology, "columns": ["left Level IIa #positiv"]},
    ('total_positive'    , 'left'  , 'IIb'             ): {"func": num_from_pathology, "columns": ["left Level IIb #positiv"]},
    ('total_positive'    , 'left'  , 'III'             ): {"func": num_from_pathology, "columns": ["left Level III #positiv"]},
    ('total_positive'    , 'left'  , 'IV'              ): {"func": num_from_pathology, "columns": ["left Level IV #positiv"]},
    ('total_positive'    , 'left'  , 'V'               ): {"func": num_super_from_pathology, "kwargs": {"lnl": "V", "side": "left"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('total_positive'    , 'left'  , 'Va'              ): {"func": num_from_pathology, "columns": ["left Level Va #positiv"]},
    ('total_positive'    , 'left'  , 'Vb'              ): {"func": num_from_pathology, "columns": ["left Level Vb #positiv"]},
    ('total_positive'    , 'right' , 'I'               ): {"func": num_super_from_pathology, "kwargs": {"lnl": "I", "side": "right"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('total_positive'    , 'right' , 'Ia'              ): {"func": num_from_pathology, "columns": ["right Level Ia #positiv "]},
    ('total_positive'    , 'right' , 'Ib'              ): {"func": num_from_pathology, "columns": ["right Level Ib #positiv"]},
    ('total_positive'    , 'right' , 'II'              ): {"func": num_super_from_pathology, "kwargs": {"lnl": "II", "side": "right"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('total_positive'    , 'right' , 'IIa'             ): {"func": num_from_pathology, "columns": ["right Level IIa #positiv"]},
    ('total_positive'    , 'right' , 'IIb'             ): {"func": num_from_pathology, "columns": ["right Level IIb #positiv"]},
    ('total_positive'    , 'right' , 'III'             ): {"func": num_from_pathology, "columns": ["right Level III #positiv"]},
    ('total_positive'    , 'right' , 'IV'              ): {"func": num_from_pathology, "columns": ["right Level IV #positiv"]},
    ('total_positive'    , 'right' , 'V'               ): {"func": num_super_from_pathology, "kwargs": {"lnl": "V", "side": "right"}, "columns": PATHOLOGY_COLS_POSITIVE},
    ('total_positive'    , 'right' , 'Va'              ): {"func": num_from_pathology, "columns": ["right Level Va #positiv"]},
    ('total_positive'    , 'right' , 'Vb'              ): {"func": num_from_pathology, "columns": ["right Level Vb #positiv"]},
}
