"""
This module defines how the command `lyscripts data lyproxify` should handle the
`raw.csv` data in order to transform it into a LyProX-compatible `data.csv` file.

The most important definitions in here are the list `exclude` and the dictionary
`column_map` that defines how to construct the new columns based on the `raw.csv` data.
"""
import re
from dateutil.parser import ParserError, parse
import numpy as np

import icd10



def robust_date(entry, *_args, **_kwargs):
    """
    Robustly parse a date string.
    """
    try:
        parsed_dt = parse(entry)
        return parsed_dt.strftime("%Y-%m-%d")
    except ParserError:
        return None
    except TypeError:
        return None


def robust_int(entry, *_args, **_kwargs):
    """
    Robustly convert a string to int, if possible.
    """
    try:
        return int(entry)
    except ValueError:
        return None
    except TypeError:
        return None


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


def strip_letters(entry, *_args, **_kwargs):
    """
    Remove letters following a number.
    """
    try:
        return int(entry)
    except ValueError:
        return int(entry[0])


# The below list specifies which function to run for which columns in the `raw.csv` to
# find out if patients/rows should be excluded in the lyproxified `data.csv`.
# In the 2021 CLB Oropharynx dataset, no patients need to be excluded.
exclude = []


# This dictionary's keys define the columns the lyproxified `data.csv` should contain
# and how to construct them from the columns existing in the `raw.csv` data.
column_map = {
    # Patient information
	('patient' , '#'    , 'id'             ): {"func": str, "columns": ['Num patient']},
	('patient' , '#'    , 'institution'    ): {"default": "Centre Léon Bérard"},
	('patient' , '#'    , 'sex'            ): {"func": lambda x, *a, **k: "male" if x == 0 else "female", "columns": ['sexe']},
	('patient' , '#'    , 'age'            ): {"func": robust_int, "columns": ['age']},
	('patient' , '#'    , 'diagnose_date'  ): {"func": robust_date, "columns": ["date d'origine"]},
	('patient' , '#'    , 'alcohol_abuse'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['consom.éthylique']},
	('patient' , '#'    , 'nicotine_abuse' ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['tabagisme']},
    ('patient' , '#'    , 'pack_years'     ): {"func": robust_int, "columns": ['tabagisme_PA']},
	('patient' , '#'    , 'hpv_status'     ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['p16']},
	('patient' , '#'    , 'neck_dissection'): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ["curage_coté"]},
    ('patient' , '#'    , 'tnm_edition'    ): {"default": 8},
	('patient' , '#'    , 'n_stage'        ): {"func": strip_letters, "columns": ['pN_TNM8']},
	('patient' , '#'    , 'm_stage'        ): {"func": lambda x, *a, **k: 2 if x == 'x' else int(x), "columns": ['cM']},

    # Tumor information
	('tumor'   , '1'    , 'location'       ): {"default": "oropharynx"},
	('tumor'   , '1'    , 'subsite'        ): {"func": get_subsite, "columns": ["locT_code ICD O3"]},
    ('tumor'   , '1'    , 'central'        ): {"func": lambda x, *a, **k: False if x == 0 else None, "columns": ['latéralité']},
	('tumor'   , '1'    , 'extension'      ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['latéralité']},
	('tumor'   , '1'    , 'volume'         ): {"default": None},
	('tumor'   , '1'    , 'stage_prefix'   ): {"default": "c"},
	('tumor'   , '1'    , 't_stage'        ): {"func": strip_letters, "columns": ['cT_TNM8']},

    #
	('diagnostic_consensus', 'info'  , 'date'): {"func": robust_date, "columns": ["date d'origine"]},
	('diagnostic_consensus', 'ipsi'  , 'Ia'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['HL_cN+_aireIa']},
	('diagnostic_consensus', 'ipsi'  , 'Ib'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['HL_cN+_aireIb']},
	('diagnostic_consensus', 'ipsi'  , 'II'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['HL_cN+_aireII']},
	('diagnostic_consensus', 'ipsi'  , 'III' ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['HL_cN+_aireIII']},
	('diagnostic_consensus', 'ipsi'  , 'IV'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['HL_cN+_aireIV(a/b)']},
	('diagnostic_consensus', 'ipsi'  , 'V'   ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['HL_cN+_aireV(a/b/c)']},
	('diagnostic_consensus', 'ipsi'  , 'VII' ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['HL_VII (RP)']},
	('diagnostic_consensus', 'contra', 'Ia'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['CL_cN+_aireIa']},
	('diagnostic_consensus', 'contra', 'Ib'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['CL_cN+_aireIb']},
	('diagnostic_consensus', 'contra', 'II'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['CL_cN+_aireII']},
	('diagnostic_consensus', 'contra', 'III' ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['CL_cN+_aireIII']},
	('diagnostic_consensus', 'contra', 'IV'  ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['CL_cN+_aireIV(a/b)']},
	('diagnostic_consensus', 'contra', 'V'   ): {"func": lambda x, *a, **k: False if x == 0 else True, "columns": ['CL_cN+_aireV(a/b/c)']},
	('diagnostic_consensus', 'contra', 'VII' ): {"default": None},

    # pathology in boolean form
	('pathology'         , 'info'  , 'date'): {"func": robust_date, "columns": ["date d'origine"]},
	('pathology'         , 'ipsi'  , 'Ia'  ): {"func": parse_pathology, "columns": ['HL_Ia_(+)']},
	('pathology'         , 'ipsi'  , 'Ib'  ): {"func": parse_pathology, "columns": ['HL_Ib_(+)']},
	('pathology'         , 'ipsi'  , 'II'  ): {"func": parse_pathology, "columns": ['HL_II_(+)']},
	('pathology'         , 'ipsi'  , 'III' ): {"func": parse_pathology, "columns": ['HL_III_(+)']},
	('pathology'         , 'ipsi'  , 'IV'  ): {"func": parse_pathology, "columns": ['HL_IV_(+)']},
	('pathology'         , 'ipsi'  , 'V'   ): {"func": parse_pathology, "columns": ['HL_V_(+)']},
	('pathology'         , 'ipsi'  , 'VII' ): {"func": parse_pathology, "columns": ['HL_VII_(+)']},
	('pathology'         , 'contra', 'Ia'  ): {"func": parse_pathology, "columns": ['CL_Ia_(+)']},
	('pathology'         , 'contra', 'Ib'  ): {"func": parse_pathology, "columns": ['CL_Ib_(+)']},
	('pathology'         , 'contra', 'II'  ): {"func": parse_pathology, "columns": ['CL_II_(+)']},
	('pathology'         , 'contra', 'III' ): {"func": parse_pathology, "columns": ['CL_III_(+)']},
	('pathology'         , 'contra', 'IV'  ): {"func": parse_pathology, "columns": ['CL_IV_(+)']},
	('pathology'         , 'contra', 'V'   ): {"func": parse_pathology, "columns": ['CL_V_(+)']},
	('pathology'         , 'contra', 'VII' ): {"default": None},

    # how many LNLs were dissected
	('total_dissected'   , 'info'  , 'date'): {"func": robust_date, "columns": ["date d'origine"]},
    ('total_dissected'   , 'ipsi'  , 'all' ): {"func": robust_int, "columns": ['total gg analysés HL']},
	('total_dissected'   , 'ipsi'  , 'Ia'  ): {"func": robust_int, "columns": ['HL_Ia_analysés']},
	('total_dissected'   , 'ipsi'  , 'Ib'  ): {"func": robust_int, "columns": ['HL_Ib_analysés']},
	('total_dissected'   , 'ipsi'  , 'II'  ): {"func": robust_int, "columns": ['HL_II_analysés']},
	('total_dissected'   , 'ipsi'  , 'III' ): {"func": robust_int, "columns": ['HL_III_analysés']},
	('total_dissected'   , 'ipsi'  , 'IV'  ): {"func": robust_int, "columns": ['HL_IV_analysés']},
	('total_dissected'   , 'ipsi'  , 'V'   ): {"func": robust_int, "columns": ['HL_V_analysés']},
	('total_dissected'   , 'ipsi'  , 'VII' ): {"func": robust_int, "columns": ['HL_VII_analysés']},
    ('total_dissected'   , 'contra', 'all' ): {"func": robust_int, "columns": ['total gg analysés CL']},
	('total_dissected'   , 'contra', 'Ia'  ): {"func": robust_int, "columns": ['CL_Ia_analysés']},
	('total_dissected'   , 'contra', 'Ib'  ): {"func": robust_int, "columns": ['CL_Ib_analysés']},
	('total_dissected'   , 'contra', 'II'  ): {"func": robust_int, "columns": ['CL_II_analysés']},
	('total_dissected'   , 'contra', 'III' ): {"func": robust_int, "columns": ['CL_III_analysés']},
	('total_dissected'   , 'contra', 'IV'  ): {"func": robust_int, "columns": ['CL_IV_analysés']},
	('total_dissected'   , 'contra', 'V'   ): {"func": robust_int, "columns": ['CL_V_analysés']},

    # how many of the dissected LNLs were positive
	('positive_dissected', 'info'  , 'date'): {"func": robust_date, "columns": ["date d'origine"]},
    ('positive_dissected', 'ipsi'  , 'all' ): {"func": robust_int, "columns": ['total gg (+) HL']},
	('positive_dissected', 'ipsi'  , 'Ia'  ): {"func": robust_int, "columns": ['HL_Ia_(+)']},
	('positive_dissected', 'ipsi'  , 'Ib'  ): {"func": robust_int, "columns": ['HL_Ib_(+)']},
	('positive_dissected', 'ipsi'  , 'II'  ): {"func": robust_int, "columns": ['HL_II_(+)']},
	('positive_dissected', 'ipsi'  , 'III' ): {"func": robust_int, "columns": ['HL_III_(+)']},
	('positive_dissected', 'ipsi'  , 'IV'  ): {"func": robust_int, "columns": ['HL_IV_(+)']},
	('positive_dissected', 'ipsi'  , 'V'   ): {"func": robust_int, "columns": ['HL_V_(+)']},
	('positive_dissected', 'ipsi'  , 'VII' ): {"func": robust_int, "columns": ['HL_VII_(+)']},
    ('positive_dissected', 'contra', 'all' ): {"func": robust_int, "columns": ['total gg (+) CL']},
	('positive_dissected', 'contra', 'Ia'  ): {"func": robust_int, "columns": ['CL_Ia_(+)']},
	('positive_dissected', 'contra', 'Ib'  ): {"func": robust_int, "columns": ['CL_Ib_(+)']},
	('positive_dissected', 'contra', 'II'  ): {"func": robust_int, "columns": ['CL_II_(+)']},
	('positive_dissected', 'contra', 'III' ): {"func": robust_int, "columns": ['CL_III_(+)']},
	('positive_dissected', 'contra', 'IV'  ): {"func": robust_int, "columns": ['CL_IV_(+)']},
	('positive_dissected', 'contra', 'V'   ): {"func": robust_int, "columns": ['CL_V_(+)']},
}
