"""
Map the `raw.csv` data from the 2021-clb-oropharynx cohort to the `data.csv` file.

This module defines how the command `lyscripts data lyproxify` (see
[here](rmnldwg.github.io/lyscripts) for the documentation of the `lyscripts` module)
should handle the `raw.csv` data that was extracted at the Inselspital Bern in order
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

import icd10
import numpy as np
from dateutil.parser import ParserError, parse


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
        for i in [0, 1]:
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
EXCLUDE = []


# This dictionary's keys define the columns the lyproxified `data.csv` should contain
# and how to construct them from the columns existing in the `raw.csv` data.
COLUMN_MAP = {
    # Patient information
    "patient": {
        "__doc__": (
            "General information about the patient’s condition can be found under this"
            " top-level header."
        ),
        "#": {
            "__doc__": (
                "The second level under patient has no meaning and exists solely as a"
                " filler."
            ),
            "id": {
                "__doc__": "Enumeration of the patients.",
                "func": str,
                "columns": ["Num patient"],
            },
            "institution": {
                "__doc__": "The clinic where the data was extracted.",
                "default": "Centre Léon Bérard",
            },
            "sex": {
                "__doc__": "The biological sex of the patient.",
                "func": lambda x, *a, **k: "male" if x == 0 else "female",
                "columns": ["sexe"],
            },
            "age": {
                "__doc__": "The age of the patient at the time of diagnosis.",
                "func": robust_int,
                "columns": ["age"],
            },
            "diagnose_date": {
                "__doc__": (
                    "Date of diagnosis (format `YYYY-mm-dd`) defined as the date of"
                    " first histological confirmation of HNSCC."
                ),
                "func": robust_date,
                "columns": ["date d'origine"],
            },
            "alcohol_abuse": {
                "__doc__": (
                    "`true` for patients who stated that they consume alcohol"
                    " regularly, `false` otherwise."
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["consom.éthylique"],
            },
            "nicotine_abuse": {
                "__doc__": (
                    "`true` for patients who have been regular smokers (> 10 pack"
                    " years), `false` otherwise."
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["tabagisme"],
            },
            "pack_years": {
                "__doc__": "Number of pack years of smoking hitory of the patient.",
                "func": robust_int,
                "columns": ["tabagisme_PA"],
            },
            "hpv_status": {
                "__doc__": (
                    "`true` for patients with human papilloma virus associated tumors"
                    " (as defined by p16 immunohistochemistry)."
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["p16"],
            },
            "neck_dissection": {
                "__doc__": (
                    "Indicates whether the patient has received a neck dissection as"
                    " part of the treatment."
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["curage_coté"],
            },
            "tnm_edition": {
                "__doc__": (
                    "The edition of the TNM classification used to classify the"
                    " patient."
                ),
                "default": 8,
            },
            "n_stage": {
                "__doc__": (
                    "The N category of the patient, indicating the degree of spread to"
                    " regional lymph nodes."
                ),
                "func": strip_letters,
                "columns": ["pN_TNM8"],
            },
            "m_stage": {
                "__doc__": (
                    "The M category of the patient, encoding the presence of distant"
                    " metastases. `-1` represents `'X'`."
                ),
                "func": lambda x, *a, **k: -1 if x == "x" else int(x),
                "columns": ["cM"],
            },
        },
    },
    # Tumor information
    "tumor": {
        "__doc__": "Information about tumors is stored under this top-level header.",
        "1": {
            "__doc__": (
                "The second level enumerates the synchronous tumors. In our database,"
                " no patient has had a second tumor but this structure of the file"
                " allows us to include such patients in the future. The third-level"
                " headers are the same for each tumor.."
            ),
            "location": {
                "__doc__": (
                    "Anatomic location of the tumor. Since this dataset contains only"
                    " oropharyngeal SCC patients, this is always `oropharynx`."
                ),
                "default": "oropharynx",
            },
            "subsite": {
                "__doc__": "The subsite of the tumor, specified by ICD-O-3 code.",
                "func": get_subsite,
                "columns": ["locT_code ICD O3"],
            },
            "central": {
                "__doc__": (
                    "`true` when the tumor is located centrally on the mid-sagittal"
                    " plane."
                ),
                "func": lambda x, *a, **k: False if x == 0 else None,
                "columns": ["latéralité"],
            },
            "extension": {
                "__doc__": "`true` when the tumor extends over the mid-sagittal plane.",
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["latéralité"],
            },
            "volume": {"__doc__": "The volume of the tumor in cm^3.", "default": None},
            "stage_prefix": {
                "__doc__": (
                    "Prefix modifier of the T-category. Can be `“c”` or `“p”`. In this"
                    " dataset, only the clinically assessed T-category is available."
                ),
                "default": "c",
            },
            "t_stage": {
                "__doc__": "T-category of the tumor, according to TNM staging.",
                "func": strip_letters,
                "columns": ["cT_TNM8"],
            },
        },
    },
    "diagnostic_consensus": {
        "__doc__": (
            "This top-level header contains the per-level clinical consensus on lymph"
            " node involvement. It was assessed based on different diagnostic"
            " modalities like CT or MRI."
        ),
        "info": {
            "__doc__": (
                "The second level header contains general information on the diagnostic"
                " consensus."
            ),
            "date": {
                "__doc__": (
                    "The date of the diagnostic consensus (same as date of diagnosis)."
                ),
                "func": robust_date,
                "columns": ["date d'origine"],
            },
        },
        "ipsi": {
            "__doc__": (
                "These columns report the involvement based on the diagnostic consensus"
                " for ipsilateral LNLs."
            ),
            "Ia": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["HL_cN+_aireIa"],
            },
            "Ib": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["HL_cN+_aireIb"],
            },
            "II": {
                "__doc__": (
                    "For example, the clinical involvement of level II lymph nodes."
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["HL_cN+_aireII"],
            },
            "III": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["HL_cN+_aireIII"],
            },
            "IV": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["HL_cN+_aireIV(a/b)"],
            },
            "V": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["HL_cN+_aireV(a/b/c)"],
            },
            "VII": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["HL_VII (RP)"],
            },
        },
        "contra": {
            "__doc__": (
                "These columns report the involvement based on the diagnostic consensus"
                " for contralateral LNLs."
            ),
            "Ia": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["CL_cN+_aireIa"],
            },
            "Ib": {
                "__doc__": (
                    "For example, the clinical involvement of sub-level Ib lymph nodes."
                ),
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["CL_cN+_aireIb"],
            },
            "II": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["CL_cN+_aireII"],
            },
            "III": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["CL_cN+_aireIII"],
            },
            "IV": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["CL_cN+_aireIV(a/b)"],
            },
            "V": {
                "func": lambda x, *a, **k: False if x == 0 else True,
                "columns": ["CL_cN+_aireV(a/b/c)"],
            },
            "VII": {"default": None},
        },
    },
    # pathology in boolean form
    "pathology": {
        "__doc__": (
            "Columns under this header contain pathologically assessed involvement"
            " information for each LNL."
        ),
        "info": {
            "__doc__": (
                "The second level header contains general information on the pathology."
            ),
            "date": {
                "__doc__": "The date of the pathology (same as date of diagnosis).",
                "func": robust_date,
                "columns": ["date d'origine"],
            },
        },
        "ipsi": {
            "__doc__": (
                "Here, we report the ipsilateral LNL involvement based on the"
                " pathology."
            ),
            "Ia": {"func": parse_pathology, "columns": ["HL_Ia_(+)"]},
            "Ib": {"func": parse_pathology, "columns": ["HL_Ib_(+)"]},
            "II": {"func": parse_pathology, "columns": ["HL_II_(+)"]},
            "III": {"func": parse_pathology, "columns": ["HL_III_(+)"]},
            "IV": {"func": parse_pathology, "columns": ["HL_IV_(+)"]},
            "V": {
                "__doc__": (
                    "For instance, the pathologically assessed involvement of level V"
                    " lymph nodes."
                ),
                "func": parse_pathology,
                "columns": ["HL_V_(+)"],
            },
            "VII": {"func": parse_pathology, "columns": ["HL_VII_(+)"]},
        },
        "contra": {
            "__doc__": "The contralateral LNL involvement based on the pathology.",
            "Ia": {"func": parse_pathology, "columns": ["CL_Ia_(+)"]},
            "Ib": {"func": parse_pathology, "columns": ["CL_Ib_(+)"]},
            "II": {
                "__doc__": (
                    "E.g., the pathologically assessed involvement of sub-level II"
                    " lymph nodes."
                ),
                "func": parse_pathology,
                "columns": ["CL_II_(+)"],
            },
            "III": {"func": parse_pathology, "columns": ["CL_III_(+)"]},
            "IV": {"func": parse_pathology, "columns": ["CL_IV_(+)"]},
            "V": {"func": parse_pathology, "columns": ["CL_V_(+)"]},
            "VII": {"default": None},
        },
    },
    # how many LNLs were dissected
    "total_dissected": {
        "__doc__": "The total number of lymph nodes resected per LNL.",
        "info": {
            "__doc__": (
                "The second level header contains general information on the pathology."
            ),
            "date": {
                "__doc__": "The date of the pathology (same as date of diagnosis).",
                "func": robust_date,
                "columns": ["date d'origine"],
            },
        },
        "ipsi": {
            "__doc__": "Number of dissected lymph nodes in ipsilateral LNLs.",
            "all": {
                "__doc__": (
                    "Like the total number of lymph nodes dissected in all ipsilateral"
                    " LNLs."
                ),
                "func": robust_int,
                "columns": ["total gg analysés HL"],
            },
            "Ia": {"func": robust_int, "columns": ["HL_Ia_analysés"]},
            "Ib": {"func": robust_int, "columns": ["HL_Ib_analysés"]},
            "II": {"func": robust_int, "columns": ["HL_II_analysés"]},
            "III": {"func": robust_int, "columns": ["HL_III_analysés"]},
            "IV": {
                "__doc__": "Or the number of dissected lymph nodes in level IV only.",
                "func": robust_int,
                "columns": ["HL_IV_analysés"],
            },
            "V": {"func": robust_int, "columns": ["HL_V_analysés"]},
            "VII": {"func": robust_int, "columns": ["HL_VII_analysés"]},
        },
        "contra": {
            "__doc__": "Number of dissected lymph nodes in contralateral LNLs.",
            "all": {
                "__doc__": (
                    "Consequently, these column contains the total number of lymph"
                    " nodes dissected in all contralateral LNLs."
                ),
                "func": robust_int,
                "columns": ["total gg analysés CL"],
            },
            "Ia": {
                "__doc__": (
                    "And this column reports only the number of dissected lymph nodes"
                    " in level Ia."
                ),
                "func": robust_int,
                "columns": ["CL_Ia_analysés"],
            },
            "Ib": {"func": robust_int, "columns": ["CL_Ib_analysés"]},
            "II": {"func": robust_int, "columns": ["CL_II_analysés"]},
            "III": {"func": robust_int, "columns": ["CL_III_analysés"]},
            "IV": {"func": robust_int, "columns": ["CL_IV_analysés"]},
            "V": {"func": robust_int, "columns": ["CL_V_analysés"]},
        },
    },
    # how many of the dissected LNLs were positive
    "positive_dissected": {
        "__doc__": "The number of metastatic lymph nodes found in the dissected LNLs.",
        "info": {
            "__doc__": (
                "The second level header contains general information on the pathology."
            ),
            "date": {
                "__doc__": "The date of the pathology (same as date of diagnosis).",
                "func": robust_date,
                "columns": ["date d'origine"],
            },
        },
        "ipsi": {
            "__doc__": (
                "Columns under this second-level header report the number of metastatic"
                " lymph nodes found in the dissected ipsilateral LNLs."
            ),
            "all": {
                "__doc__": (
                    "First, the total number of metastatic lymph nodes found in all"
                    " ipsilateral LNLs."
                ),
                "func": robust_int,
                "columns": ["total gg (+) HL"],
            },
            "Ia": {"func": robust_int, "columns": ["HL_Ia_(+)"]},
            "Ib": {"func": robust_int, "columns": ["HL_Ib_(+)"]},
            "II": {"func": robust_int, "columns": ["HL_II_(+)"]},
            "III": {"func": robust_int, "columns": ["HL_III_(+)"]},
            "IV": {"func": robust_int, "columns": ["HL_IV_(+)"]},
            "V": {"func": robust_int, "columns": ["HL_V_(+)"]},
            "VII": {
                "__doc__": (
                    "And then, for instance, the number of metastatic lymph nodes found"
                    " in level VII only."
                ),
                "func": robust_int,
                "columns": ["HL_VII_(+)"],
            },
        },
        "contra": {
            "__doc__": (
                "Columns under this second-level header report the number of metastatic"
                " lymph nodes found in the dissected contralateral LNLs."
            ),
            "all": {
                "__doc__": (
                    "In analogy to the ipsilateral LNLs, this column states the total"
                    " number of metastatic lymph nodes found in all contralateral LNLs."
                ),
                "func": robust_int,
                "columns": ["total gg (+) CL"],
            },
            "Ia": {"func": robust_int, "columns": ["CL_Ia_(+)"]},
            "Ib": {"func": robust_int, "columns": ["CL_Ib_(+)"]},
            "II": {"func": robust_int, "columns": ["CL_II_(+)"]},
            "III": {
                "__doc__": (
                    "And this column reports the number of metastatic lymph nodes found"
                    " in level III only."
                ),
                "func": robust_int,
                "columns": ["CL_III_(+)"],
            },
            "IV": {"func": robust_int, "columns": ["CL_IV_(+)"]},
            "V": {"func": robust_int, "columns": ["CL_V_(+)"]},
        },
    },
}
