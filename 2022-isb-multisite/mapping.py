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
        "I": [*ALL_FALSE, True, True, False, False, False, False, False, False],
        "II": [*ALL_FALSE, False, False, True, True, False, False, False, False],
        "V": [*ALL_FALSE, False, False, False, False, False, False, True, True],
    },
    "right": {
        #      Ia     Ib     IIa    IIb    III    IV     Va     Vb     left side
        "I": [True, True, False, False, False, False, False, False, *ALL_FALSE],
        "II": [False, False, True, True, False, False, False, False, *ALL_FALSE],
        "V": [False, False, False, False, False, False, True, True, *ALL_FALSE],
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
        for i in [0, 1]:
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

    The clinical stage is only used if the pathological stage is not available.
    """
    map_dict = {
        1: 1,
        2: 1,
        3: 2,
        4: 3,
        5: 4,
        6: 4,
        None: None,  # robust(int) returns None if an exception is thrown
    }
    if pd.isna(pathological) or pathological == "n/a":
        return map_dict[robust(int)(clinical)]

    return map_dict[robust(int)(pathological)]


def map_n_stage(entry, *_args, **_kwargs):
    """
    Map their N-stage encoding to actual N-stage.
    """
    try:
        return {0: 0, 1: 1, 2: 2, 3: 2, 4: 2, 5: 2, 6: 3}[robust(int)(entry)]
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


def _from_pathology(entry) -> tuple[dict[str, int], bool]:
    """
    Infer how many nodes in an LNL where investigated/positive per resection. And if the
    LNL showed signs of extracapsular extension (ECE).

    The way the data was collected is a bit tricky: Generally, they report the number
    of nodes in an LNL that were investigated or positive (depending on the column one
    looks at). But if multiple levels were resected and investigated en bloc, they
    wrote the finding in each LNL and appended a letter to the number. So, if LNL I was
    resected together with LNL II and they found in total 10 nodes, they would write
    `LNL I: 10a` and `LNL II: 10a`.

    Additionally, if extracapsular extension was found, they would add 100 to the
    number. And if parts of an LNL were resected with another LNL, but another part of
    the LNL was investigated on its own, they would write something like `12 + 4b`.
    """
    res = {}
    # If not available, leave empty
    if entry is None or entry == "n/a" or pd.isna(entry):
        return res, False

    # split entry at '+' that may be surrounded by whitespace
    separator = re.compile(r"\s?\+\s?")
    marks = separator.split(entry)

    if marks is None or len(marks) == 0:
        return res, False

    # find numbers like '103b'
    pattern = re.compile("([0-9]{1,3})([a-z])?")

    # iterate through marks and check if they have been resected with other LNLs
    for mark in marks:
        match = pattern.search(mark)
        num = int(match.group(1)) % 100
        has_ece = int(match.group(1)) // 100 == 1
        symbol = match.group(2) or "this"
        res[symbol] = num + res.get(symbol, 0)

    return res, has_ece


def num_from_pathology(entry, *_args, **_kwargs) -> Optional[int]:
    """
    Infer number of involved nodes in LNL from pathology report.
    """
    res, _ = _from_pathology(entry)

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
    Infer number of involved lymph nodes in super LNL (e.g. I, II and V) from pathology.

    This involves checking if other LNLs have been resected with the LNL in question.
    In that case, we do not know if the LNL in question was involved or if it was only
    one of the co-resected LNLs.
    """
    lnl_results = [_from_pathology(e)[0] for e in lnl_entries]
    symbols = {s for lnl_res in lnl_results for s in lnl_res.keys() if s != "this"}

    known_lnl_invs = np.array([lnl_res.get("this") for lnl_res in lnl_results])
    try:
        res = sum(known_lnl_invs[SUBLVL_PATTERN[side][lnl]])
    except TypeError:
        res = None

    for symbol in symbols:
        symbol_nums = np.array([lnl_res.get(symbol, 0) for lnl_res in lnl_results])
        symbol_pattern = symbol_nums > 0
        if all(symbol_pattern == SUBLVL_PATTERN[side][lnl]):
            res = (sum(symbol_nums[SUBLVL_PATTERN[side][lnl]]) / 2.0) + (res or 0)

    return res


def binary_super_from_pathology(*lnl_entries, lnl="I", side="left") -> Optional[bool]:
    """
    Infer if super LNL is involved from pathology.
    """
    num = num_super_from_pathology(*lnl_entries, lnl=lnl, side=side)

    if num is None:
        return None

    return num > 0


def map_ece(*lnl_entries, **_kwargs):
    """
    Infer from the provided columns if the patient had LNL involvement with
    extra-capsular extension.

    In the data, this is incoded by the value 100 being added to the number of
    positive LNLs.
    """
    return any(_from_pathology(e)[1] for e in lnl_entries)


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


EXCLUDE = [("Exclusion", lambda s: s == 1)]


# dictionary indicating how to transform the columns
COLUMN_MAP = {
    # Patient information
    "patient": {
        "__doc__": "This top-level header contains general patient information.",
        "#": {
            "__doc__": (
                "The second level header for the `patient` columns is only a "
                "placeholder."
            ),
            "id": {
                "__doc__": "The local study ID.",
                "func": str,
                "columns": ["Local Study ID"],
            },
            "institution": {
                "__doc__": "The institution where the patient was treated.",
                "default": "Inselspital Bern",
            },
            "sex": {
                "__doc__": "The biological sex of the patient.",
                "func": lambda x, *a, **k: "female" if x == 1 else "male",
                "columns": ["Gender"],
            },
            "age": {
                "__doc__": "The age of the patient at the time of diagnosis.",
                "func": robust(int),
                "columns": ["Age diagnose"],
            },
            "diagnose_date": {
                "__doc__": "The date of diagnosis.",
                "func": robust(smpl_date),
                "columns": ["Date of diagnosis"],
            },
            "alcohol_abuse": {
                "__doc__": (
                    "Whether the patient was abusingly drinking alcohol at the time of"
                    " diagnosis."
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["Alcohol"],
            },
            "nicotine_abuse": {
                "__doc__": (
                    "Whether the patient was considered a smoker. This is set to"
                    " `False`, when the patient had zero pack-years"
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["Smoking"],
            },
            "hpv_status": {
                "__doc__": "The HPV p16 status of the patient.",
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["p16"],
            },
            "neck_dissection": {
                "__doc__": (
                    "Whether the patient underwent a neck dissection. In this dataset, "
                    "all patients underwent a neck dissection."
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["side of ND"],
            },
            "tnm_edition": {
                "__doc__": "The edition of the TNM classification used.",
                "func": robust(int),
                "columns": ["TNM Edition"],
            },
            "n_stage": {
                "__doc__": "The pN category of the patient (pathologically assessed).",
                "func": map_n_stage,
                "columns": ["pN"],
            },
            "m_stage": {
                "__doc__": "The M category of the patient.",
                "func": lambda x, *a, **k: 2 if x == "x" else robust(int)(x),
                "columns": ["M-Stage"],
            },
            "extracapsular": {
                "__doc__": "Whether the patient had extracapsular spread in any LNL.",
                "func": map_ece,
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
        },
    },
    # Tumor information
    "tumor": {
        "__doc__": "This top-level header contains general tumor information.",
        "1": {
            "__doc__": "This second-level header enumerates synchronous tumors.",
            "location": {
                "__doc__": "The location of the tumor.",
                "func": map_location,
                "columns": ["Primary Tumor"],
            },
            "subsite": {
                "__doc__": "The subsite of the tumor, specified by ICD-O-3 code.",
                "func": get_subsite,
                "columns": ["ICD-O-3 code"],
            },
            "side": {
                "__doc__": (
                    "Whether the tumor occured on the right or left side of the"
                    " mid-sagittal plane."
                ),
                "func": map_side,
                "columns": ["side"],
            },
            "central": {
                "__doc__": "Whether the tumor was located centrally or not.",
                "func": lambda x, *a, **k: True if robust(int)(x) == 3 else False,
                "columns": ["side"],
            },
            "extension": {
                "__doc__": "Whether the tumor extended over the mid-sagittal line.",
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["Extension over the mid-sagital plane"],
            },
            "volume": {"__doc__": "The volume of the tumor in cm^3.", "default": None},
            "stage_prefix": {
                "__doc__": "The prefix of the T category.",
                "default": "p",
            },
            "t_stage": {
                "__doc__": "The T category of the tumor.",
                "func": map_t_stage,
                "columns": ["cT", "pT"],
            },
        },
    },
    # CT & MRI are displayed in the same table. A diagnose is considered MRI,
    # when available and CT only if MRI is not recorded (and CT available)
    "CT": {
        "__doc__": (
            "This top-level header contains involvement information from the CT scan."
        ),
        "info": {
            "__doc__": (
                "This second-level header contains general information about the CT"
                " scan."
            ),
            "date": {
                "__doc__": "The date of the CT scan.",
                "func": get_ct_date,
                "columns": ["Date of preoperativ  CT Thorax", MRI_OR_CT_COL],
            },
        },
        "left": {
            "__doc__": "This describes the observed involvement of the left LNLs.",
            "I": {"default": None},
            "Ia": {"func": map_ct, "columns": ["left Level Ia", MRI_OR_CT_COL]},
            "Ib": {"func": map_ct, "columns": ["left Level Ib", MRI_OR_CT_COL]},
            "II": {"default": None},
            "IIa": {"func": map_ct, "columns": ["left Level IIa", MRI_OR_CT_COL]},
            "IIb": {"func": map_ct, "columns": ["left Level IIb", MRI_OR_CT_COL]},
            "III": {"func": map_ct, "columns": ["left Level III", MRI_OR_CT_COL]},
            "IV": {"func": map_ct, "columns": ["left Level IV", MRI_OR_CT_COL]},
            "V": {"default": None},
            "Va": {
                "__doc__": (
                    "As an example, this describes the clincal involvement of the left"
                    " LNL Va, as observed in a CT scan."
                ),
                "func": map_ct,
                "columns": ["left Level Va", MRI_OR_CT_COL],
            },
            "Vb": {"func": map_ct, "columns": ["left Level Vb", MRI_OR_CT_COL]},
        },
        "right": {
            "__doc__": "This describes the observed involvement of the right LNLs.",
            "I": {"default": None},
            "Ia": {"func": map_ct, "columns": ["right Level Ia", MRI_OR_CT_COL]},
            "Ib": {"func": map_ct, "columns": ["right Level Ib", MRI_OR_CT_COL]},
            "II": {"default": None},
            "IIa": {
                "__doc__": (
                    "While this describes the clincal involvement of the right LNL IIa,"
                    " as observed in a CT scan."
                ),
                "func": map_ct,
                "columns": ["right Level IIa", MRI_OR_CT_COL],
            },
            "IIb": {"func": map_ct, "columns": ["right Level IIb", MRI_OR_CT_COL]},
            "III": {"func": map_ct, "columns": ["right Level III", MRI_OR_CT_COL]},
            "IV": {"func": map_ct, "columns": ["right Level IV", MRI_OR_CT_COL]},
            "V": {"default": None},
            "Va": {"func": map_ct, "columns": ["right Level Va", MRI_OR_CT_COL]},
            "Vb": {"func": map_ct, "columns": ["right Level Vb", MRI_OR_CT_COL]},
        },
    },
    # CT & MRI are displayed in the same table. A diagnose is considered MRI,
    # when available and CT only if MRI is not recorded (and CT available)
    "MRI": {
        "__doc__": (
            "This top-level header contains involvement information from the MRI scan."
        ),
        "info": {
            "__doc__": (
                "This second-level header contains general information about the MRI"
                " scan."
            ),
            "date": {
                "__doc__": "The date of the MRI scan.",
                "func": get_mri_date,
                "columns": ["Date of  preoperativ  MRI", MRI_OR_CT_COL],
            },
        },
        "left": {
            "__doc__": "This describes the observed involvement of the left LNLs.",
            "I": {"default": None},
            "Ia": {
                "__doc__": (
                    "E.g., this describes the clincal involvement of the left LNL Ia,"
                    " as observed in an MRI scan."
                ),
                "func": map_mri,
                "columns": ["left Level Ia", MRI_OR_CT_COL],
            },
            "Ib": {"func": map_mri, "columns": ["left Level Ib", MRI_OR_CT_COL]},
            "II": {"default": None},
            "IIa": {"func": map_mri, "columns": ["left Level IIa", MRI_OR_CT_COL]},
            "IIb": {"func": map_mri, "columns": ["left Level IIb", MRI_OR_CT_COL]},
            "III": {"func": map_mri, "columns": ["left Level III", MRI_OR_CT_COL]},
            "IV": {"func": map_mri, "columns": ["left Level IV", MRI_OR_CT_COL]},
            "V": {"default": None},
            "Va": {"func": map_mri, "columns": ["left Level Va", MRI_OR_CT_COL]},
            "Vb": {"func": map_mri, "columns": ["left Level Vb", MRI_OR_CT_COL]},
        },
        "right": {
            "__doc__": "This describes the observed involvement of the right LNLs.",
            "I": {"default": None},
            "Ia": {"func": map_mri, "columns": ["right Level Ia", MRI_OR_CT_COL]},
            "Ib": {"func": map_mri, "columns": ["right Level Ib", MRI_OR_CT_COL]},
            "II": {"default": None},
            "IIa": {"func": map_mri, "columns": ["right Level IIa", MRI_OR_CT_COL]},
            "IIb": {"func": map_mri, "columns": ["right Level IIb", MRI_OR_CT_COL]},
            "III": {
                "__doc__": (
                    "This describes the clincal involvement of the right LNL III, as"
                    " observed in an MRI scan."
                ),
                "func": map_mri,
                "columns": ["right Level III", MRI_OR_CT_COL],
            },
            "IV": {"func": map_mri, "columns": ["right Level IV", MRI_OR_CT_COL]},
            "V": {"default": None},
            "Va": {"func": map_mri, "columns": ["right Level Va", MRI_OR_CT_COL]},
            "Vb": {"func": map_mri, "columns": ["right Level Vb", MRI_OR_CT_COL]},
        },
    },
    "PET": {
        "__doc__": (
            "This top-level header contains involvement information from the PET scan."
        ),
        "info": {
            "__doc__": (
                "This second-level header contains general information about the PET"
                " scan."
            ),
            "date": {
                "__doc__": "The date of the PET scan.",
                "func": robust(smpl_date),
                "columns": ["Date of preoperativ PET-CT"],
            },
        },
        "left": {
            "__doc__": "This describes the observed involvement of the left LNLs.",
            "I": {"default": None},
            "Ia": {"func": robust(smpl_diagnose), "columns": ["left Level Ia.1"]},
            "Ib": {"func": robust(smpl_diagnose), "columns": ["left Level Ib.1"]},
            "II": {"default": None},
            "IIa": {"func": robust(smpl_diagnose), "columns": ["left Level IIa.1"]},
            "IIb": {"func": robust(smpl_diagnose), "columns": ["left Level IIb.1"]},
            "III": {"func": robust(smpl_diagnose), "columns": ["left Level III.1"]},
            "IV": {
                "__doc__": (
                    "For instance, this describes the clincal involvement of the left"
                    " LNL IV, as observed in a PET scan."
                ),
                "func": robust(smpl_diagnose),
                "columns": ["left Level IV.1"],
            },
            "V": {"default": None},
            "Va": {"func": robust(smpl_diagnose), "columns": ["left Level Va.1"]},
            "Vb": {"func": robust(smpl_diagnose), "columns": ["left Level Vb.1"]},
        },
        "right": {
            "__doc__": "This describes the observed involvement of the right LNLs.",
            "I": {"default": None},
            "Ia": {"func": robust(smpl_diagnose), "columns": ["right Level Ia.1"]},
            "Ib": {"func": robust(smpl_diagnose), "columns": ["right Level Ib.1"]},
            "II": {"default": None},
            "IIa": {"func": robust(smpl_diagnose), "columns": ["right Level IIa.1"]},
            "IIb": {"func": robust(smpl_diagnose), "columns": ["right Level IIb.1"]},
            "III": {
                "__doc__": (
                    "On the other side, this describes the clincal involvement of the"
                    " right LNL III, as observed in a PET scan."
                ),
                "func": robust(smpl_diagnose),
                "columns": ["right Level III.1"],
            },
            "IV": {"func": robust(smpl_diagnose), "columns": ["right Level IV.1"]},
            "V": {"default": None},
            "Va": {"func": robust(smpl_diagnose), "columns": ["right Level Va.1"]},
            "Vb": {"func": robust(smpl_diagnose), "columns": ["right Level Vb.1"]},
        },
    },
    # pathology in boolean form
    "pathology": {
        "__doc__": (
            "This top-level header contains involvement information from the pathology"
            " report."
        ),
        "info": {
            "__doc__": (
                "This second-level header contains general information about the"
                " pathology report."
            ),
            "date": {
                "__doc__": "Date of the neck dissection.",
                "func": robust(smpl_date),
                "columns": ["Date of ND"],
            },
        },
        "left": {
            "__doc__": "Microscopic involvement of the left LNLs.",
            "I": {
                "__doc__": (
                    "This describes whether the left LNL I was pathologically involved"
                    " or not."
                ),
                "func": binary_super_from_pathology,
                "kwargs": {"lnl": "I", "side": "left"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "Ia": {
                "func": binary_from_pathology,
                "columns": ["left Level Ia #positiv"],
            },
            "Ib": {
                "func": binary_from_pathology,
                "columns": ["left Level Ib #positiv"],
            },
            "II": {
                "func": binary_super_from_pathology,
                "kwargs": {"lnl": "II", "side": "left"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "IIa": {
                "func": binary_from_pathology,
                "columns": ["left Level IIa #positiv"],
            },
            "IIb": {
                "func": binary_from_pathology,
                "columns": ["left Level IIb #positiv"],
            },
            "III": {
                "func": binary_from_pathology,
                "columns": ["left Level III #positiv"],
            },
            "IV": {
                "func": binary_from_pathology,
                "columns": ["left Level IV #positiv"],
            },
            "V": {
                "func": binary_super_from_pathology,
                "kwargs": {"lnl": "V", "side": "left"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "Va": {
                "func": binary_from_pathology,
                "columns": ["left Level Va #positiv"],
            },
            "Vb": {
                "func": binary_from_pathology,
                "columns": ["left Level Vb #positiv"],
            },
        },
        "right": {
            "__doc__": "Microscopic involvement of the right LNLs.",
            "I": {
                "func": binary_super_from_pathology,
                "kwargs": {"lnl": "I", "side": "right"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "Ia": {
                "func": binary_from_pathology,
                "columns": ["right Level Ia #positiv "],
            },
            "Ib": {
                "func": binary_from_pathology,
                "columns": ["right Level Ib #positiv"],
            },
            "II": {
                "func": binary_super_from_pathology,
                "kwargs": {"lnl": "II", "side": "right"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "IIa": {
                "func": binary_from_pathology,
                "columns": ["right Level IIa #positiv"],
            },
            "IIb": {
                "__doc__": (
                    "This describes whether the right sub-LNL IIb was pathologically"
                    " involved or not."
                ),
                "func": binary_from_pathology,
                "columns": ["right Level IIb #positiv"],
            },
            "III": {
                "func": binary_from_pathology,
                "columns": ["right Level III #positiv"],
            },
            "IV": {
                "func": binary_from_pathology,
                "columns": ["right Level IV #positiv"],
            },
            "V": {
                "func": binary_super_from_pathology,
                "kwargs": {"lnl": "V", "side": "right"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "Va": {
                "func": binary_from_pathology,
                "columns": ["right Level Va #positiv"],
            },
            "Vb": {
                "func": binary_from_pathology,
                "columns": ["right Level Vb #positiv"],
            },
        },
    },
    # # number of dissected nodes
    "total_dissected": {
        "__doc__": (
            "This top-level header contains information about the number of lymph nodes"
            " dissected in each LNL."
        ),
        "info": {
            "__doc__": (
                "This second-level header contains general information about the"
                " pathology report."
            ),
            "date": {
                "__doc__": "Date of the neck dissection.",
                "func": robust(smpl_date),
                "columns": ["Date of ND"],
            },
        },
        "left": {
            "__doc__": "Number of dissected lymph nodes per LNL on the left side.",
            "I": {
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "I", "side": "left"},
                "columns": PATHOLOGY_COLS_INVESTIGATED,
            },
            "Ia": {
                "func": num_from_pathology,
                "columns": ["left Level Ia #investigated"],
            },
            "Ib": {
                "func": num_from_pathology,
                "columns": ["left Level Ib #investigated"],
            },
            "II": {
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "II", "side": "left"},
                "columns": PATHOLOGY_COLS_INVESTIGATED,
            },
            "IIa": {
                "func": num_from_pathology,
                "columns": ["left Level IIa #investigated"],
            },
            "IIb": {
                "func": num_from_pathology,
                "columns": ["left Level IIb #investigated"],
            },
            "III": {
                "func": num_from_pathology,
                "columns": ["left Level III #investigated"],
            },
            "IV": {
                "func": num_from_pathology,
                "columns": ["left Level IV #investigated"],
            },
            "V": {
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "V", "side": "left"},
                "columns": PATHOLOGY_COLS_INVESTIGATED,
            },
            "Va": {
                "__doc__": "Number of dissected lymph nodes in the left sub-LNL Va.",
                "func": num_from_pathology,
                "columns": ["left Level Va #investigated"],
            },
            "Vb": {
                "func": num_from_pathology,
                "columns": ["left Level Vb #investigated"],
            },
        },
        "right": {
            "__doc__": "Number of dissected lymph nodes per LNL on the right side.",
            "I": {
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "I", "side": "right"},
                "columns": PATHOLOGY_COLS_INVESTIGATED,
            },
            "Ia": {
                "func": num_from_pathology,
                "columns": ["right Level Ia #investigated "],
            },
            "Ib": {
                "func": num_from_pathology,
                "columns": ["right Level Ib #investigated"],
            },
            "II": {
                "__doc__": "Total number of dissected lymph nodes in the right LNL II.",
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "II", "side": "right"},
                "columns": PATHOLOGY_COLS_INVESTIGATED,
            },
            "IIa": {
                "func": num_from_pathology,
                "columns": ["right Level IIa #investigated"],
            },
            "IIb": {
                "func": num_from_pathology,
                "columns": ["right Level IIb #investigated"],
            },
            "III": {
                "func": num_from_pathology,
                "columns": ["right Level III #investigated"],
            },
            "IV": {
                "func": num_from_pathology,
                "columns": ["right Level IV #investigated"],
            },
            "V": {
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "V", "side": "right"},
                "columns": PATHOLOGY_COLS_INVESTIGATED,
            },
            "Va": {
                "func": num_from_pathology,
                "columns": ["right Level Va #investigated"],
            },
            "Vb": {
                "func": num_from_pathology,
                "columns": ["right Level Vb #investigated"],
            },
        },
    },
    # # Number of positive nodes
    "total_positive": {
        "__doc__": (
            "This top-level header contains information about the number of"
            " pathologically positive lymph nodes in each LNL."
        ),
        "info": {
            "__doc__": (
                "This second-level header contains general information about the"
                " findings of metastasis by the pathologist."
            ),
            "date": {
                "__doc__": "Date of the neck dissection.",
                "func": robust(smpl_date),
                "columns": ["Date of ND"],
            },
            "largest_node_mm": {
                "__doc__": (
                    "Size of the largest lymph node in the neck dissection in mm."
                ),
                "func": robust(float),
                "columns": ["Size of largest LN (mm)"],
            },
            "largest_node_lnl": {
                "__doc__": (
                    "LNL where the largest pathological lymph node metastasis was"
                    " found."
                ),
                "func": map_to_lnl,
                "columns": ["location of largest LN", "side"],
            },
        },
        "left": {
            "__doc__": (
                "Number of pathologically positive lymph nodes per LNL on the left"
                " side."
            ),
            "I": {
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "I", "side": "left"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "Ia": {"func": num_from_pathology, "columns": ["left Level Ia #positiv"]},
            "Ib": {"func": num_from_pathology, "columns": ["left Level Ib #positiv"]},
            "II": {
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "II", "side": "left"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "IIa": {"func": num_from_pathology, "columns": ["left Level IIa #positiv"]},
            "IIb": {"func": num_from_pathology, "columns": ["left Level IIb #positiv"]},
            "III": {"func": num_from_pathology, "columns": ["left Level III #positiv"]},
            "IV": {"func": num_from_pathology, "columns": ["left Level IV #positiv"]},
            "V": {
                "__doc__": (
                    "Total number of pathologically positive lymph nodes in the left"
                    " LNL V."
                ),
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "V", "side": "left"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "Va": {"func": num_from_pathology, "columns": ["left Level Va #positiv"]},
            "Vb": {"func": num_from_pathology, "columns": ["left Level Vb #positiv"]},
        },
        "right": {
            "__doc__": (
                "Number of pathologically positive lymph nodes per LNL on the right"
                " side."
            ),
            "I": {
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "I", "side": "right"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "Ia": {"func": num_from_pathology, "columns": ["right Level Ia #positiv "]},
            "Ib": {"func": num_from_pathology, "columns": ["right Level Ib #positiv"]},
            "II": {
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "II", "side": "right"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "IIa": {
                "__doc__": (
                    "Total number of pathologically positive lymph nodes in the right"
                    " sub-LNL IIa."
                ),
                "func": num_from_pathology,
                "columns": ["right Level IIa #positiv"],
            },
            "IIb": {
                "func": num_from_pathology,
                "columns": ["right Level IIb #positiv"],
            },
            "III": {
                "func": num_from_pathology,
                "columns": ["right Level III #positiv"],
            },
            "IV": {"func": num_from_pathology, "columns": ["right Level IV #positiv"]},
            "V": {
                "func": num_super_from_pathology,
                "kwargs": {"lnl": "V", "side": "right"},
                "columns": PATHOLOGY_COLS_POSITIVE,
            },
            "Va": {"func": num_from_pathology, "columns": ["right Level Va #positiv"]},
            "Vb": {"func": num_from_pathology, "columns": ["right Level Vb #positiv"]},
        },
    },
}
