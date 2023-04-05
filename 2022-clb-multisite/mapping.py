"""
This module defines how the command `lyscripts data lyproxify` should handle the
`raw.csv` data in order to transform it into a LyProX-compatible `data.csv` file.

The most important definitions in here are the list `exclude` and the dictionary
`column_map` that defines how to construct the new columns based on the `raw.csv` data.
"""
import re

import icd10
import numpy as np
import pandas as pd
from dateutil.parser import parse


# columns that contain TNM info
TNM_COLS = [
    ('cT 7th'   , '10_lvl_1', '10_lvl_2'),
    ('cN 7th ed', '12_lvl_1', '12_lvl_2'),
    ('pT 7th ed', '16_lvl_1', '16_lvl_2'),
    ('pN 7th ed', '19_lvl_1', '19_lvl_2'),
    ('cT 8th ed', '11_lvl_1', '11_lvl_2'),
    ('cN 8th ed', '13_lvl_1', '13_lvl_2'),
    ('pT 8th ed', '17_lvl_1', '17_lvl_2'),
    ('pN 8th ed', '20_lvl_1', '20_lvl_2'),
]


def smpl_date(entry):
    """Parse date from string."""
    parsed_dt = parse(entry)
    return parsed_dt.strftime("%Y-%m-%d")


def smpl_diagnose(entry, *_args, **_kwargs):
    """Parse the diagnosis."""
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


def parse_pathology(entry, *_args, **_kwargs):
    """
    Transform number of positive nodes to `True`, `False` or `None`.
    """
    if np.isnan(entry):
        return None
    return False if entry == 0 else True


def set_diagnostic_consensus(entry, *_args, **_kwargs):
    """
    Return `False`, meaning 'healthy', when no entry about a resected LNL is available
    or when the pathology report says it was healhty. This is a hack to tackle the
    issue described here:

    https://github.com/rmnldwg/lyprox/issues/92
    """
    if np.isnan(entry) or entry == 0:
        return False
    return None


def extract_hpv(value, *_args, **_kwargs):
    """
    Translate the HPV value to a boolean.
    """
    if value == 0:
        return False
    elif value == 1:
        return True
    return None


def strip_letters(entry, *_args, **_kwargs):
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


def get_tnm_info(ct7, cn7, pt7, pn7, ct8, cn8, pt8, pn8):
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
        return pt8, pn8, 8, 'p'

    if pt7 is not None and pn7 is not None:
        return pt7, pn7, 7, 'p'

    if ct8 is not None and cn8 is not None:
        return ct8, cn8, 8, 'c'

    if ct7 is not None and cn7 is not None:
        return ct7, cn7, 7, 'c'

    raise ValueError("No consistent TNM stage could be extracted")


def get_t_category(*args, **_kwargs):
    """Extract the T-category."""
    t_cat, _, _, _, = get_tnm_info(*args)
    return t_cat


def get_n_category(*args, **_kwargs):
    """Extract the N-category."""
    _, n_cat, _, _ = get_tnm_info(*args)
    return n_cat


def get_tnm_version(*args, **_kwargs):
    """Extract the TNM version."""
    _, _, version, _ = get_tnm_info(*args)
    return version


def get_tnm_prefix(*args, **_kwargs):
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



# The below list specifies which function to run for which columns in the `raw.csv` to
# find out if patients/rows should be excluded in the lyproxified `data.csv`.
exclude = [
    (("Bauwens", "Database", "0_lvl_2"), check_excluded),
]

# This dictionary's keys define the columns the lyproxified `data.csv` should contain
# and how to construct them from the columns existing in the `raw.csv` data.
column_map = {
    # Patient information
    ('patient' , '#'    , 'id'             ): {"func": str, "columns": [("patient", "#", "id")]},
    ('patient' , '#'    , 'institution'    ): {"default": "Centre Léon Bérard"},
    ('patient' , '#'    , 'sex'            ): {"func": lambda x, *a, **k: "male" if x == 1 else "female", "columns": [("Sex", "(1=m ; 2=f)", "3_lvl_2")]},
    ('patient' , '#'    , 'age'            ): {"func": robust(int), "columns": [('Age at', 'diagnosis', '92_lvl_2')]},  # They have used the date of surgery to compute this
    ('patient' , '#'    , 'weight'         ): {"func": robust(float), "columns": [('Weight at', 'diagnosis', '54_lvl_2')]},
    ('patient' , '#'    , 'diagnose_date'  ): {"func": robust(smpl_date), "columns": [('Date of', 'surgery', '90_lvl_2')]},  # There is no date of diagnosis in the file
    ('patient' , '#'    , 'alcohol_abuse'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": [('alcool 0=n', '1=y;2=<6m', '5_lvl_2')]},
    ('patient' , '#'    , 'nicotine_abuse' ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": [('Tobacco 0=n', '1=y;2=>6m', '4_lvl_2')]},
    # ('patient' , '#'    , 'pack_years'     ): {"func": robust(int), "columns": ['tabagisme_PA']},
    ('patient' , '#'    , 'hpv_status'     ): {"func": extract_hpv, "columns": [('HPV/p16', 'status 0=no', '1=y;blank=not tested')]},
    ('patient' , '#'    , 'neck_dissection'): {"default": True},
    ('patient' , '#'    , 'tnm_edition'    ): {"func": get_tnm_version, "columns": TNM_COLS},
    ('patient' , '#'    , 'n_stage'        ): {"func": get_n_category, "columns": TNM_COLS},
    ('patient' , '#'    , 'm_stage'        ): {"default": 2},

    # Tumor information
    ('tumor'   , '1'    , 'location'       ): {"default": None},
    ('tumor'   , '1'    , 'subsite'        ): {"columns": [('ICDO-3', '1_lvl_1', '1_lvl_2')]},
    ('tumor'   , '1'    , 'central'        ): {"default": None},
    ('tumor'   , '1'    , 'extension'      ): {"default": None},
    ('tumor'   , '1'    , 'volume'         ): {"default": None},
    ('tumor'   , '1'    , 'stage_prefix'   ): {"func": get_tnm_prefix, "columns": TNM_COLS},
    ('tumor'   , '1'    , 't_stage'        ): {"func": get_t_category, "columns": TNM_COLS},

    # pathology in boolean form
    ('pathology'           , 'info'  , 'date'): {"func": robust(smpl_date), "columns": [('Date of', 'surgery', '90_lvl_2')]},
    ('pathology'           , 'ipsi'  , 'Ia'  ): {"func": parse_pathology, "columns": [('25_lvl_0', '25_lvl_1', '+')]},
    ('pathology'           , 'ipsi'  , 'Ib'  ): {"func": parse_pathology, "columns": [('27_lvl_0', '27_lvl_1', '+')]},
    ('pathology'           , 'ipsi'  , 'II'  ): {"func": parse_pathology, "columns": [('29_lvl_0', '29_lvl_1', '+')]},
    ('pathology'           , 'ipsi'  , 'III' ): {"func": parse_pathology, "columns": [('31_lvl_0', '31_lvl_1', '+')]},
    ('pathology'           , 'ipsi'  , 'IV'  ): {"func": parse_pathology, "columns": [('33_lvl_0', '33_lvl_1', '+')]},
    ('pathology'           , 'ipsi'  , 'V'   ): {"func": parse_pathology, "columns": [('35_lvl_0', '35_lvl_1', '+')]},
    ('pathology'           , 'ipsi'  , 'VII' ): {"func": parse_pathology, "columns": [('37_lvl_0', '37_lvl_1', '+')]},
    ('pathology'           , 'contra', 'Ia'  ): {"func": parse_pathology, "columns": [('39_lvl_0', '39_lvl_1', '+')]},
    ('pathology'           , 'contra', 'Ib'  ): {"func": parse_pathology, "columns": [('41_lvl_0', '41_lvl_1', '+')]},
    ('pathology'           , 'contra', 'II'  ): {"func": parse_pathology, "columns": [('43_lvl_0', '43_lvl_1', '+')]},
    ('pathology'           , 'contra', 'III' ): {"func": parse_pathology, "columns": [('45_lvl_0', '45_lvl_1', '+')]},
    ('pathology'           , 'contra', 'IV'  ): {"func": parse_pathology, "columns": [('47_lvl_0', '47_lvl_1', '+')]},
    ('pathology'           , 'contra', 'V'   ): {"func": parse_pathology, "columns": [('49_lvl_0', '49_lvl_1', '+')]},
    ('pathology'           , 'contra', 'VII' ): {"func": parse_pathology, "columns": [('51_lvl_0', '51_lvl_1', '+')]},

    # indicate negative clinical involvement when a level was not dissected (needs to be verified)
    ('diagnostic_consensus', 'info'  , 'date'): {"func": robust(smpl_date), "columns": [('Date of', 'surgery', '90_lvl_2')]},
    ('diagnostic_consensus', 'ipsi'  , 'Ia'  ): {"func": set_diagnostic_consensus, "columns": [('25_lvl_0', '25_lvl_1', '+')]},
    ('diagnostic_consensus', 'ipsi'  , 'Ib'  ): {"func": set_diagnostic_consensus, "columns": [('27_lvl_0', '27_lvl_1', '+')]},
    ('diagnostic_consensus', 'ipsi'  , 'II'  ): {"func": set_diagnostic_consensus, "columns": [('29_lvl_0', '29_lvl_1', '+')]},
    ('diagnostic_consensus', 'ipsi'  , 'III' ): {"func": set_diagnostic_consensus, "columns": [('31_lvl_0', '31_lvl_1', '+')]},
    ('diagnostic_consensus', 'ipsi'  , 'IV'  ): {"func": set_diagnostic_consensus, "columns": [('33_lvl_0', '33_lvl_1', '+')]},
    ('diagnostic_consensus', 'ipsi'  , 'V'   ): {"func": set_diagnostic_consensus, "columns": [('35_lvl_0', '35_lvl_1', '+')]},
    # ('diagnostic_consensus', 'ipsi'  , 'VII' ): {"func": set_diagnostic_consensus, "columns": [('37_lvl_0', '37_lvl_1', '+')]},
    ('diagnostic_consensus', 'contra', 'Ia'  ): {"func": set_diagnostic_consensus, "columns": [('39_lvl_0', '39_lvl_1', '+')]},
    ('diagnostic_consensus', 'contra', 'Ib'  ): {"func": set_diagnostic_consensus, "columns": [('41_lvl_0', '41_lvl_1', '+')]},
    ('diagnostic_consensus', 'contra', 'II'  ): {"func": set_diagnostic_consensus, "columns": [('43_lvl_0', '43_lvl_1', '+')]},
    ('diagnostic_consensus', 'contra', 'III' ): {"func": set_diagnostic_consensus, "columns": [('45_lvl_0', '45_lvl_1', '+')]},
    ('diagnostic_consensus', 'contra', 'IV'  ): {"func": set_diagnostic_consensus, "columns": [('47_lvl_0', '47_lvl_1', '+')]},
    ('diagnostic_consensus', 'contra', 'V'   ): {"func": set_diagnostic_consensus, "columns": [('49_lvl_0', '49_lvl_1', '+')]},
    # ('diagnostic_consensus', 'contra', 'VII' ): {"func": set_diagnostic_consensus, "columns": [('51_lvl_0', '51_lvl_1', '+')]},

    # how many LNLs were dissected
    ('total_dissected'     , 'info'  , 'date'): {"func": robust(smpl_date), "columns": [('Date of', 'surgery', '90_lvl_2')]},
    ('total_dissected'     , 'ipsi'  , 'Ia'  ): {"func": robust(int), "columns": [('Homolateral neck node infiltration', 'LIa', 'tot')]},
    ('total_dissected'     , 'ipsi'  , 'Ib'  ): {"func": robust(int), "columns": [('26_lvl_0', 'LIb', 'tot')]},
    ('total_dissected'     , 'ipsi'  , 'II'  ): {"func": robust(int), "columns": [('28_lvl_0', 'LII', 'tot')]},
    ('total_dissected'     , 'ipsi'  , 'III' ): {"func": robust(int), "columns": [('30_lvl_0', 'LIII', 'tot')]},
    ('total_dissected'     , 'ipsi'  , 'IV'  ): {"func": robust(int), "columns": [('32_lvl_0', 'LIV', 'tot')]},
    ('total_dissected'     , 'ipsi'  , 'V'   ): {"func": robust(int), "columns": [('34_lvl_0', 'LV', 'tot')]},
    ('total_dissected'     , 'ipsi'  , 'VII' ): {"func": robust(int), "columns": [('36_lvl_0', 'LVII', 'tot')]},
    ('total_dissected'     , 'contra', 'Ia'  ): {"func": robust(int), "columns": [('Heterolateral neck node infiltration', 'LIa', 'tot')]},
    ('total_dissected'     , 'contra', 'Ib'  ): {"func": robust(int), "columns": [('40_lvl_0', 'LIb', 'tot')]},
    ('total_dissected'     , 'contra', 'II'  ): {"func": robust(int), "columns": [('42_lvl_0', 'LII', 'tot')]},
    ('total_dissected'     , 'contra', 'III' ): {"func": robust(int), "columns": [('44_lvl_0', 'LIII', 'tot')]},
    ('total_dissected'     , 'contra', 'IV'  ): {"func": robust(int), "columns": [('46_lvl_0', 'LIV', 'tot')]},
    ('total_dissected'     , 'contra', 'V'   ): {"func": robust(int), "columns": [('48_lvl_0', 'LV', 'tot')]},
    ('total_dissected'     , 'contra', 'VII' ): {"func": robust(int), "columns": [('50_lvl_0', 'LVII', 'tot')]},

    # how many of the dissected LNLs were positive
    ('positive_dissected'  , 'info'  , 'date'): {"func": robust(smpl_date), "columns": [('Date of', 'surgery', '90_lvl_2')]},
    ('positive_dissected'  , 'ipsi'  , 'Ia'  ): {"func": robust(int), "columns": [('25_lvl_0', '25_lvl_1', '+')]},
    ('positive_dissected'  , 'ipsi'  , 'Ib'  ): {"func": robust(int), "columns": [('27_lvl_0', '27_lvl_1', '+')]},
    ('positive_dissected'  , 'ipsi'  , 'II'  ): {"func": robust(int), "columns": [('29_lvl_0', '29_lvl_1', '+')]},
    ('positive_dissected'  , 'ipsi'  , 'III' ): {"func": robust(int), "columns": [('31_lvl_0', '31_lvl_1', '+')]},
    ('positive_dissected'  , 'ipsi'  , 'IV'  ): {"func": robust(int), "columns": [('33_lvl_0', '33_lvl_1', '+')]},
    ('positive_dissected'  , 'ipsi'  , 'V'   ): {"func": robust(int), "columns": [('35_lvl_0', '35_lvl_1', '+')]},
    ('positive_dissected'  , 'ipsi'  , 'VII' ): {"func": robust(int), "columns": [('37_lvl_0', '37_lvl_1', '+')]},
    ('positive_dissected'  , 'contra', 'Ia'  ): {"func": robust(int), "columns": [('39_lvl_0', '39_lvl_1', '+')]},
    ('positive_dissected'  , 'contra', 'Ib'  ): {"func": robust(int), "columns": [('41_lvl_0', '41_lvl_1', '+')]},
    ('positive_dissected'  , 'contra', 'II'  ): {"func": robust(int), "columns": [('43_lvl_0', '43_lvl_1', '+')]},
    ('positive_dissected'  , 'contra', 'III' ): {"func": robust(int), "columns": [('45_lvl_0', '45_lvl_1', '+')]},
    ('positive_dissected'  , 'contra', 'IV'  ): {"func": robust(int), "columns": [('47_lvl_0', '47_lvl_1', '+')]},
    ('positive_dissected'  , 'contra', 'V'   ): {"func": robust(int), "columns": [('49_lvl_0', '49_lvl_1', '+')]},
    ('positive_dissected'  , 'contra', 'VII' ): {"func": robust(int), "columns": [('51_lvl_0', '51_lvl_1', '+')]},
}
