"""
Map the `raw.csv` data from the 2023-clb-multisite cohort to the `data.csv` file.

This module defines how the command `lyscripts data lyproxify` (see
[here](rmnldwg.github.io/lyscripts) for the documentation of the `lyscripts` module)
should handle the `raw.csv` data that was extracted at the Centre Léon Bérard in order
to transform it into a [LyProX](https://lyprox.org)-compatible `data.csv` file.

The most important definitions in here are the list `EXCLUDE` and the dictionary
`COLUMN_MAP` that defines how to construct the new columns based on the `raw.csv` data.
They are described in more detail below:

---

### <kbd>global</kbd> `EXCLUDE`

List of tuples specifying which function to run for which columns to find out if
patients/rows should be excluded in the lyproxified `data.csv`.

The first element of each tuple is the flattened multi-index column name, the second
element is the function to run on the column to determine if a patient/row should be
excluded:

```python
EXCLUDE = [
    (column_name, check_function),
]
```

Essentially, a row is excluded, if for that row `check_function(raw_data[column_name])`
evaluates to `True`.

More information can be found in the
[documentation](https://rmnldwg.github.io/lyscripts/lyscripts/data/lyproxify.html#exclude_patients)
of the `lyproxify` function.

---

### <kbd>global</kbd> `COLUMN_MAP`

This is the actual mapping dictionary that describes how to transform the `raw.csv`
table into the `data.csv` table that can be fed into and understood by
[LyProX](https://lyprox.org).

See [here](https://rmnldwg.github.io/lyscripts/lyscripts/data/lyproxify.html#transform_to_lyprox)
for details on how this dictionary is used by the `lyproxify` script.

It contains a tree-like structure that is human-readable and mimics the tree of
multi-level headers in the final `data.csv` file. For every column in the final
`data.csv` file, the dictionary describes from which columns in the `raw.csv` file the
data should be extracted and what function should be applied to it.

It also contains a `__doc__` key for every sub-dictionary that describes what the
respective column is about. This is used to generate the documentation for the
`README.md` file of this data.

---
"""
import re
from collections.abc import Callable
from typing import Any

import icd10
import numpy as np
import pandas as pd
from dateutil.parser import parse

# columns that contain TNM info
TNM_COLS = [
    ("cT 7th", "10_lvl_1", "10_lvl_2"),
    ("cN 7th ed", "12_lvl_1", "12_lvl_2"),
    ("pT 7th ed", "16_lvl_1", "16_lvl_2"),
    ("pN 7th ed", "19_lvl_1", "19_lvl_2"),
    ("cT 8th ed", "11_lvl_1", "11_lvl_2"),
    ("cN 8th ed", "13_lvl_1", "13_lvl_2"),
    ("pT 8th ed", "17_lvl_1", "17_lvl_2"),
    ("pN 8th ed", "20_lvl_1", "20_lvl_2"),
]

# columns that detail how many nodes were resected/positive in the LNLs Ib through III
IB_TO_III_DISSECTED = {
    "total": {
        "ipsi": [
            ("26_lvl_0", "LIb", "tot"),
            ("28_lvl_0", "LII", "tot"),
            ("30_lvl_0", "LIII", "tot"),
        ],
        "contra": [
            ("40_lvl_0", "LIb", "tot"),
            ("42_lvl_0", "LII", "tot"),
            ("44_lvl_0", "LIII", "tot"),
        ],
    },
    "positive": {
        "ipsi": [
            ("27_lvl_0", "27_lvl_1", "+"),
            ("29_lvl_0", "29_lvl_1", "+"),
            ("31_lvl_0", "31_lvl_1", "+"),
        ],
        "contra": [
            ("41_lvl_0", "41_lvl_1", "+"),
            ("43_lvl_0", "43_lvl_1", "+"),
            ("45_lvl_0", "45_lvl_1", "+"),
        ],
    },
}


def smpl_date(entry: str) -> str:
    """Parse date from string."""
    parsed_dt = parse(entry)
    return parsed_dt.strftime("%Y-%m-%d")


def smpl_diagnose(entry: str | int, *_args, **_kwargs) -> bool:
    """Parse the diagnosis."""
    return {
        0: False,
        1: True,
        2: True,
    }[robust(int)(entry)]


def robust(func: Callable) -> Any | None:
    """
    Wrapper that makes any type-conversion function 'robust' by simply returning
    `None` whenever any exception is thrown.
    """

    # pylint: disable=bare-except
    def wrapper(entry, *_args, **_kwargs):
        if pd.isna(entry):
            return None
        try:
            return func(entry)
        except:
            return None

    return wrapper


def get_subsite(entry: str, *_args, **_kwargs) -> str | None:
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


def parse_pathology(entry, *_args, **_kwargs) -> bool | None:
    """
    Transform number of positive nodes to `True`, `False` or `None`.
    """
    if np.isnan(entry):
        return None
    return False if entry == 0 else True


def set_diagnostic_consensus(entry, *_args, **_kwargs):
    """
    Return `False`, meaning 'healthy', when no entry about a resected LNL is available.
    This is a hack to tackle theissue described here:

    https://github.com/rmnldwg/lyprox/issues/92
    """
    return False if np.isnan(entry) else None


def extract_hpv(value: int | None, *_args, **_kwargs) -> bool | None:
    """
    Translate the HPV value to a boolean.
    """
    if value == 0:
        return False
    elif value == 1:
        return True
    return None


def strip_letters(entry: str, *_args, **_kwargs) -> int:
    """
    Remove letters following a number.
    """
    try:
        return int(entry)
    except ValueError:
        return int(entry[0])


def clean_cat(cat: str) -> int:
    """
    Extract T or N category as integer from the respective string.
    I.e., turn 'pN2+' into 2.
    """
    pattern = re.compile(r"[cp][TN]([0-4])[\s\S]*")
    match = pattern.match(str(cat))
    try:
        return int(match.group(1))
    except AttributeError:
        return None


def get_tnm_info(ct7, cn7, pt7, pn7, ct8, cn8, pt8, pn8) -> tuple[int, int, int, str]:
    """
    Determine the TNM edition used based on which versions are available for T and/or
    N category.
    """
    ct7 = clean_cat(ct7)
    cn7 = clean_cat(cn7)
    pt7 = clean_cat(pt7)
    pn7 = clean_cat(pn7)
    ct8 = clean_cat(ct8)
    cn8 = clean_cat(cn8)
    pt8 = clean_cat(pt8)
    pn8 = clean_cat(pn8)

    if pt8 is not None and pn8 is not None:
        return pt8, pn8, 8, "p"

    if pt7 is not None and pn7 is not None:
        return pt7, pn7, 7, "p"

    if ct8 is not None and cn8 is not None:
        return ct8, cn8, 8, "c"

    if ct7 is not None and cn7 is not None:
        return ct7, cn7, 7, "c"

    raise ValueError("No consistent TNM stage could be extracted")


def get_t_category(*args, **_kwargs) -> int:
    """Extract the T-category."""
    (
        t_cat,
        _,
        _,
        _,
    ) = get_tnm_info(*args)
    return t_cat


def get_n_category(*args, **_kwargs) -> int:
    """Extract the N-category."""
    _, n_cat, _, _ = get_tnm_info(*args)
    return n_cat


def get_tnm_version(*args, **_kwargs) -> int:
    """Extract the TNM version."""
    _, _, version, _ = get_tnm_info(*args)
    return version


def get_tnm_prefix(*args, **_kwargs) -> str:
    """Extract the TNM prefix."""
    _, _, _, prefix = get_tnm_info(*args)
    return prefix


def check_excluded(column: pd.Series) -> pd.Index:
    """
    Check if a patient/row is excluded based on the content of a `column`.

    For the 2022 CLB multisite dataset this is the case when the first column with the
    three-level header `("Bauwens", "Database", "0_lvl_2")` is not empty or does not
    contain the character `'n'`.
    """
    is_empty = column.isna()
    contains_n = column == "n"
    is_excluded = np.all([~is_empty, ~contains_n], axis=0)
    return pd.Index(is_excluded)


def sum_columns(*columns, **_kwargs) -> int:
    """
    Sum the values of multiple columns.
    """
    res = 0
    for column in columns:
        add = robust(int)(column)
        if add is None:
            return None
        res += add

    return res


# Find the documentation for the variable below in the module-level docstring.
EXCLUDE = [
    (("Bauwens", "Database", "0_lvl_2"), check_excluded),
]

# Find the documentation for the variable below in the module-level docstring.
COLUMN_MAP = {
    "patient": {
        "__doc__": "This top-level header contains general patient information.",
        "#": {
            "__doc__": (
                "The second level header for the `patient` columns is only a "
                "placeholder."
            ),
            "id": {
                "__doc__": "The patient ID.",
                "func": str,
                "columns": [("patient", "#", "id")],
            },
            "institution": {
                "__doc__": "The institution where the patient was treated.",
                "default": "Centre Léon Bérard",
            },
            "sex": {
                "__doc__": "The biological sex of the patient.",
                "func": lambda x, *a, **k: "male" if x == 1 else "female",
                "columns": [("Sex", "(1=m ; 2=f)", "3_lvl_2")],
            },
            "age": {
                "__doc__": "The age of the patient at the time of diagnosis.",
                "func": robust(int),
                "columns": [("Age at", "diagnosis", "91_lvl_2")],
            },
            "weight": {
                "__doc__": "The weight of the patient at the time of diagnosis.",
                "func": robust(float),
                "columns": [("Weight at", "diagnosis", "54_lvl_2")],
            },
            "diagnose_date": {
                "__doc__": (
                    "The date of surgery because the raw file does not specify a "
                    "date of diagnosis."
                ),
                "func": robust(smpl_date),
                "columns": [("Date of", "surgery", "89_lvl_2")],
            },
            "alcohol_abuse": {
                "__doc__": (
                    "Whether the patient was abusingly drinking alcohol at the time of"
                    " diagnosis."
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": [("alcool 0=n", "1=y;2=<6m", "5_lvl_2")],
            },
            "nicotine_abuse": {
                "__doc__": (
                    "Whether the patient was smoking nicotine at the time of diagnosis."
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": [("Tobacco 0=n", "1=y;2=>6m", "4_lvl_2")],
            },
            "hpv_status": {
                "__doc__": "The HPV p16 status of the patient.",
                "func": extract_hpv,
                "columns": [("HPV/p16", "status 0=no", "1=y;blank=not tested")],
            },
            "neck_dissection": {
                "__doc__": (
                    "Whether the patient underwent a neck dissection. In this dataset, "
                    "all patients underwent a neck dissection."
                ),
                "default": True,
            },
            "tnm_edition": {
                "__doc__": "The edition of the TNM classification used.",
                "func": get_tnm_version,
                "columns": TNM_COLS,
            },
            "n_stage": {
                "__doc__": "The pN category of the patient (pathologically assessed).",
                "func": get_n_category,
                "columns": TNM_COLS,
            },
            "m_stage": {
                "__doc__": "The M category of the patient. `-1` refers to `'X'`.",
                "default": -1,
            },
            "extracapsular": {
                "__doc__": (
                    "Whether the patient had extracapsular spread. In this dataset, "
                    "this information is only globally available, not for each "
                    "individual lymph node level."
                ),
                "func": robust(bool),
                "columns": [("ENE", "0=n;1=y", "7_lvl_2")],
            },
        },
    },
    # Tumor information
    "tumor": {
        "__doc__": "This top-level header contains general tumor information.",
        "1": {
            "__doc__": "The second level header enumerates synchronous tumors.",
            "location": {
                "__doc__": "The location of the tumor. This is empty for all patients because we can later infer it from the subsite's ICD-O-3 code.",
                "default": None,
            },
            "subsite": {
                "__doc__": "The subsite of the tumor, specified by ICD-O-3 code.",
                "func": lambda x, *_a, **_kw: x,
                "columns": [("ICDO-3", "1_lvl_1", "1_lvl_2")],
            },
            "central": {
                "__doc__": (
                    "Whether the tumor is located centrally w.r.t. the mid-sagittal "
                    "plane."
                ),
                "default": None,
            },
            "extension": {
                "__doc__": "Whether the tumor extended over the mid-sagittal line.",
                "default": None,
            },
            "volume": {
                "__doc__": "The volume of the tumor in cm^3.",
                "default": None,
            },
            "stage_prefix": {
                "__doc__": "The prefix of the T category.",
                "func": get_tnm_prefix,
                "columns": TNM_COLS,
            },
            "t_stage": {
                "__doc__": "The T category of the tumor.",
                "func": get_t_category,
                "columns": TNM_COLS,
            },
        },
    },
    # Involvement information from pathology
    "pathology": {
        "__doc__": (
            "This top-level header contains information from the pathology that "
            "received the LNLs resected during the neck dissection."
        ),
        "info": {
            "__doc__": "This second-level header contains general information.",
            "date": {
                "__doc__": "The date of the pathology report (same as surgery).",
                "func": robust(smpl_date),
                "columns": [("Date of", "surgery", "89_lvl_2")],
            },
        },
        "ipsi": {
            "__doc__": "This reports the involvement of the ipsilateral LNLs.",
            "Ia": {
                "func": parse_pathology,
                "columns": [("25_lvl_0", "25_lvl_1", "+")],
            },
            "Ib": {
                "func": parse_pathology,
                "columns": [("27_lvl_0", "27_lvl_1", "+")],
            },
            "II": {
                "func": parse_pathology,
                "columns": [("29_lvl_0", "29_lvl_1", "+")],
            },
            "III": {
                "__doc__": (
                    "For example, this column reports the involvement of the"
                    " ipsilateral LNL III."
                ),
                "func": parse_pathology,
                "columns": [("31_lvl_0", "31_lvl_1", "+")],
            },
            "IV": {
                "func": parse_pathology,
                "columns": [("33_lvl_0", "33_lvl_1", "+")],
            },
            "V": {
                "func": parse_pathology,
                "columns": [("35_lvl_0", "35_lvl_1", "+")],
            },
            "VII": {
                "func": parse_pathology,
                "columns": [("37_lvl_0", "37_lvl_1", "+")],
            },
        },
        "contra": {
            "__doc__": "This reports the involvement of the contralateral LNLs.",
            "Ia": {
                "func": parse_pathology,
                "columns": [("39_lvl_0", "39_lvl_1", "+")],
            },
            "Ib": {
                "func": parse_pathology,
                "columns": [("41_lvl_0", "41_lvl_1", "+")],
            },
            "II": {
                "func": parse_pathology,
                "columns": [("43_lvl_0", "43_lvl_1", "+")],
            },
            "III": {
                "func": parse_pathology,
                "columns": [("45_lvl_0", "45_lvl_1", "+")],
            },
            "IV": {
                "func": parse_pathology,
                "columns": [("47_lvl_0", "47_lvl_1", "+")],
            },
            "V": {
                "__doc__": (
                    "This column reports the pathologic involvement of the"
                    " contralateral LNL V."
                ),
                "func": parse_pathology,
                "columns": [("49_lvl_0", "49_lvl_1", "+")],
            },
            "VII": {
                "func": parse_pathology,
                "columns": [("51_lvl_0", "51_lvl_1", "+")],
            },
        },
    },
    # Diagnostic consensus
    "diagnostic_consensus": {
        "__doc__": (
            "This top-level header contains information about the diagnostic "
            "consensus, which we assumed to be negative for each LNL that was not "
            "resected during the neck dissection. However, we do not know if it was "
            "positive for resected patients. This means, all columns under this "
            "top-level header are essentially inferred from looking at missing "
            "entries under the pathology columns."
        ),
        "info": {
            "__doc__": "This second-level header contains general information.",
            "date": {
                "__doc__": "The date of the diagnostic consensus (same as surgery).",
                "func": robust(smpl_date),
                "columns": [("Date of", "surgery", "89_lvl_2")],
            },
        },
        "ipsi": {
            "__doc__": "This reports the diagnostic consensus of the ipsilateral LNLs.",
            "Ia": {
                "func": set_diagnostic_consensus,
                "columns": [("25_lvl_0", "25_lvl_1", "+")],
            },
            "Ib": {
                "__doc__": (
                    "E.g., this column reports the diagnostic consensus of the"
                    " ipsilateral LNL Ib."
                ),
                "func": set_diagnostic_consensus,
                "columns": [("27_lvl_0", "27_lvl_1", "+")],
            },
            "II": {
                "func": set_diagnostic_consensus,
                "columns": [("29_lvl_0", "29_lvl_1", "+")],
            },
            "III": {
                "func": set_diagnostic_consensus,
                "columns": [("31_lvl_0", "31_lvl_1", "+")],
            },
            "IV": {
                "func": set_diagnostic_consensus,
                "columns": [("33_lvl_0", "33_lvl_1", "+")],
            },
            "V": {
                "func": set_diagnostic_consensus,
                "columns": [("35_lvl_0", "35_lvl_1", "+")],
            },
        },
        "contra": {
            "__doc__": (
                "This reports the diagnostic consensus of the contralateral LNLs."
            ),
            "Ia": {
                "func": set_diagnostic_consensus,
                "columns": [("39_lvl_0", "39_lvl_1", "+")],
            },
            "Ib": {
                "func": set_diagnostic_consensus,
                "columns": [("41_lvl_0", "41_lvl_1", "+")],
            },
            "II": {
                "func": set_diagnostic_consensus,
                "columns": [("43_lvl_0", "43_lvl_1", "+")],
            },
            "III": {
                "__doc__": (
                    "Under this column, we report the diagnostic consensus of the"
                    " contralateral LNL III."
                ),
                "func": set_diagnostic_consensus,
                "columns": [("45_lvl_0", "45_lvl_1", "+")],
            },
            "IV": {
                "func": set_diagnostic_consensus,
                "columns": [("47_lvl_0", "47_lvl_1", "+")],
            },
            "V": {
                "func": set_diagnostic_consensus,
                "columns": [("49_lvl_0", "49_lvl_1", "+")],
            },
        },
    },
    # Number of dissected lymph nodes
    "total_dissected": {
        "__doc__": (
            "This top-level header contains information about the total number "
            "of dissected and pathologically investigated lymph nodes per LNL."
        ),
        "info": {
            "__doc__": "This second-level header contains general information.",
            "date": {
                "__doc__": "The date of the neck dissection.",
                "func": robust(smpl_date),
                "columns": [("Date of", "surgery", "89_lvl_2")],
            },
        },
        "ipsi": {
            "__doc__": (
                "This reports the total number of dissected lymph nodes per "
                "ipsilateral LNL."
            ),
            "Ia": {
                "func": robust(int),
                "columns": [("Homolateral neck node infiltration", "LIa", "tot")],
            },
            "Ib": {
                "func": robust(int),
                "columns": [("26_lvl_0", "LIb", "tot")],
            },
            "II": {
                "__doc__": (
                    "For instance, this column reports the total number of "
                    "dissected lymph nodes in ipsilateral LNL II."
                ),
                "func": robust(int),
                "columns": [("28_lvl_0", "LII", "tot")],
            },
            "III": {
                "func": robust(int),
                "columns": [("30_lvl_0", "LIII", "tot")],
            },
            "IV": {
                "func": robust(int),
                "columns": [("32_lvl_0", "LIV", "tot")],
            },
            "V": {
                "func": robust(int),
                "columns": [("34_lvl_0", "LV", "tot")],
            },
            "VII": {
                "func": robust(int),
                "columns": [("36_lvl_0", "LVII", "tot")],
            },
            "Ib_to_III": {
                "__doc__": (
                    "This column reports the total number of dissected lymph "
                    "nodes in ipsilateral LNL Ib to III. This column exists "
                    "for convenience because we created a figure based on this."
                ),
                "func": sum_columns,
                "columns": IB_TO_III_DISSECTED["total"]["ipsi"],
            },
        },
        "contra": {
            "__doc__": (
                "This reports the total number of dissected lymph nodes per "
                "contralateral LNL."
            ),
            "Ia": {
                "func": robust(int),
                "columns": [("Heterolateral neck node infiltration", "LIa", "tot")],
            },
            "Ib": {
                "func": robust(int),
                "columns": [("40_lvl_0", "LIb", "tot")],
            },
            "II": {
                "func": robust(int),
                "columns": [("42_lvl_0", "LII", "tot")],
            },
            "III": {
                "func": robust(int),
                "columns": [("44_lvl_0", "LIII", "tot")],
            },
            "IV": {
                "func": robust(int),
                "columns": [("46_lvl_0", "LIV", "tot")],
            },
            "V": {
                "func": robust(int),
                "columns": [("48_lvl_0", "LV", "tot")],
            },
            "VII": {
                "__doc__": (
                    "While this column reports the total number of dissected "
                    "lymph nodes in contralateral LNL VII."
                ),
                "func": robust(int),
                "columns": [("50_lvl_0", "LVII", "tot")],
            },
            "Ib_to_III": {
                "__doc__": (
                    "This column reports the total number of dissected lymph "
                    "nodes in contralateral LNL Ib to III. This column exists "
                    "for convenience because we created a figure based on this."
                ),
                "func": sum_columns,
                "columns": IB_TO_III_DISSECTED["total"]["contra"],
            },
        },
    },
    # Number of positive lymph nodes
    "positive_dissected": {
        "__doc__": (
            "This top-level header contains information about the number of "
            "dissected lymph nodes per LNL that were pathologically found to "
            "be positive."
        ),
        "info": {
            "__doc__": "This second-level header contains general information.",
            "date": {
                "__doc__": "The date of the neck dissection.",
                "func": robust(smpl_date),
                "columns": [("Date of", "surgery", "89_lvl_2")],
            },
        },
        "ipsi": {
            "__doc__": (
                "This reports the number of dissected lymph nodes per ipsilateral "
                "LNL that were pathologically found to be positive."
            ),
            "Ia": {
                "func": robust(int),
                "columns": [("25_lvl_0", "25_lvl_1", "+")],
            },
            "Ib": {
                "func": robust(int),
                "columns": [("27_lvl_0", "27_lvl_1", "+")],
            },
            "II": {
                "func": robust(int),
                "columns": [("29_lvl_0", "29_lvl_1", "+")],
            },
            "III": {
                "func": robust(int),
                "columns": [("31_lvl_0", "31_lvl_1", "+")],
            },
            "IV": {
                "__doc__": (
                    "Here, we report the number of metastatic lymph nodes in"
                    " ipsilateral LNL IV."
                ),
                "func": robust(int),
                "columns": [("33_lvl_0", "33_lvl_1", "+")],
            },
            "V": {
                "func": robust(int),
                "columns": [("35_lvl_0", "35_lvl_1", "+")],
            },
            "VII": {
                "func": robust(int),
                "columns": [("37_lvl_0", "37_lvl_1", "+")],
            },
            "Ib_to_III": {
                "__doc__": (
                    "This column reports the number of metastatic dissected lymph "
                    "nodes in ipsilateral LNL Ib to III. This column exists "
                    "for convenience because we created a figure based on this."
                ),
                "func": sum_columns,
                "columns": IB_TO_III_DISSECTED["positive"]["ipsi"],
            },
        },
        "contra": {
            "__doc__": (
                "This reports the number of dissected lymph nodes per contralateral "
                "LNL that were pathologically found to be positive."
            ),
            "Ia": {
                "__doc__": (
                    "And this column reports the number of metastatic lymph nodes in"
                    " contralateral LNL Ia."
                ),
                "func": robust(int),
                "columns": [("39_lvl_0", "39_lvl_1", "+")],
            },
            "Ib": {
                "func": robust(int),
                "columns": [("41_lvl_0", "41_lvl_1", "+")],
            },
            "II": {
                "func": robust(int),
                "columns": [("43_lvl_0", "43_lvl_1", "+")],
            },
            "III": {
                "func": robust(int),
                "columns": [("45_lvl_0", "45_lvl_1", "+")],
            },
            "IV": {
                "func": robust(int),
                "columns": [("47_lvl_0", "47_lvl_1", "+")],
            },
            "V": {
                "func": robust(int),
                "columns": [("49_lvl_0", "49_lvl_1", "+")],
            },
            "VII": {
                "func": robust(int),
                "columns": [("51_lvl_0", "51_lvl_1", "+")],
            },
            "Ib_to_III": {
                "__doc__": (
                    "This column reports the number of metastatic dissected lymph "
                    "nodes in contralateral LNL Ib to III. This column exists "
                    "for convenience because we created a figure based on this."
                ),
                "func": sum_columns,
                "columns": IB_TO_III_DISSECTED["positive"]["contra"],
            },
        },
    },
}
