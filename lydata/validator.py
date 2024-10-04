"""Module to transform to and validate the CSV schema of the lydata datasets.

Here we define the function :py:func:`construct_schema` to dynamically create a
:py:class:`pandera.DataFrameSchema` that we can use to validate that a given
:py:class:`~pandas.DataFrame` conforms to the minimum requirements of the lyDATA
datasets.

Currently, we only publish the :py:func:`validate_datasets` function that validates all
datasets that are found by the function :py:func:`~lydata.loader.available_datasets`.
In the future, we may want to make this more flexible.

In this module, we also provide the :py:func:`transform_to_lyprox` function that can be
used to transform any raw data into the format that can be uploaded to the `LyProX`_
platform database.

.. _LyProX: https://lyprox.org
"""

import logging
from typing import Any

import pandas as pd
from pandera import Check, Column, DataFrameSchema
from pandera.errors import SchemaError

from lydata.loader import available_datasets

logger = logging.getLogger(__name__)

_NULLABLE_OPTIONAL = {"required": False, "nullable": True}
_NULLABLE_OPTIONAL_BOOLEAN_COLUMN = Column(
    dtype="boolean",
    coerce=True,
    **_NULLABLE_OPTIONAL,
)
_DATE_CHECK = Check.str_matches(r"^\d{4}-\d{2}-\d{2}$")
_LNLS = [
    "I",
    "Ia",
    "Ib",
    "II",
    "IIa",
    "IIb",
    "III",
    "IV",
    "V",
    "Va",
    "Vb",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
]


class ParsingError(Exception):
    """Error while parsing the CSV file."""


patient_columns = {
    ("patient", "#", "institution"): Column(str),
    ("patient", "#", "sex"): Column(str, Check.str_matches(r"^(male|female)$")),
    ("patient", "#", "age"): Column(int),
    ("patient", "#", "weight"): Column(
        float, Check.greater_than(0), **_NULLABLE_OPTIONAL
    ),
    ("patient", "#", "diagnose_date"): Column(str, _DATE_CHECK),
    ("patient", "#", "alcohol_abuse"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
    ("patient", "#", "nicotine_abuse"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
    ("patient", "#", "hpv_status"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
    ("patient", "#", "neck_dissection"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
    ("patient", "#", "tnm_edition"): Column(int, Check.in_range(7, 8)),
    ("patient", "#", "n_stage"): Column(int, Check.in_range(0, 3)),
    ("patient", "#", "m_stage"): Column(int, Check.in_range(-1, 1)),
}

tumor_columns = {
    ("tumor", "1", "subsite"): Column(str, Check.str_matches(r"^C\d{2}(\.\d)?$")),
    ("tumor", "1", "t_stage"): Column(int, Check.in_range(0, 4)),
    ("tumor", "1", "stage_prefix"): Column(str, Check.str_matches(r"^(p|c)$")),
    ("tumor", "1", "volume"): Column(
        float, Check.greater_than(0), **_NULLABLE_OPTIONAL
    ),
    ("tumor", "1", "central"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
    ("tumor", "1", "extension"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
}


def get_modality_columns(
    modality: str,
    lnls: list[str] = _LNLS,
) -> dict[tuple[str, str, str], Column]:
    """Get the validation columns for a given modality."""
    cols = {(modality, "info", "date"): Column(str, _DATE_CHECK, **_NULLABLE_OPTIONAL)}

    for side in ["ipsi", "contra"]:
        for lnl in lnls:
            cols[(modality, side, lnl)] = _NULLABLE_OPTIONAL_BOOLEAN_COLUMN

    return cols


def construct_schema(
    modalities: list[str],
    lnls: list[str] = _LNLS,
) -> DataFrameSchema:
    """Construct a :py:class:`pandera.DataFrameSchema` for the lydata datasets."""
    schema = DataFrameSchema(patient_columns).add_columns(tumor_columns)

    for modality in modalities:
        schema = schema.add_columns(get_modality_columns(modality, lnls))

    return schema


def validate_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    skip_disk: bool = False,
    repo: str = "rmnldwg/lydata",
    ref: str = "main",
    **kwargs,
) -> None:
    """Validate all lydata datasets.

    The arguments of this function are directly passed to the
    :py:func:`available_datasets` function to determine which datasets to validate.

    Keyword arguments beyond the ones that :py:func:`available_datasets` accepts are
    passed to the :py:meth:`~lydata.loader.Dataset.load` method of the
    :py:class:`~lydata.loader.Dataset` instances.
    """
    lydata_schema = construct_schema(
        modalities=["pathology", "diagnostic_consensus", "PET", "CT", "FNA", "MRI"],
    )

    for data_conf in available_datasets(
        year=year,
        institution=institution,
        subsite=subsite,
        skip_disk=skip_disk,
        repo=repo,
        ref=ref,
    ):
        dataset = data_conf.load(**kwargs)
        try:
            lydata_schema.validate(dataset)
            logger.info(f"Schema validation passed for {data_conf!r}.")
        except SchemaError as schema_err:
            message = f"Schema validation failed for {data_conf!r}."
            logger.error(message, exc_info=schema_err)
            raise Exception(message) from schema_err


def delete_private_keys(nested: dict) -> dict:
    """Delete private keys from a nested dictionary.

    A 'private' key is a key whose name starts with an underscore. For example:

    >>> delete_private_keys({"patient": {"__doc__": "some patient info", "age": 61}})
    {'patient': {'age': 61}}
    >>> delete_private_keys({"patient": {"age": 61}})
    {'patient': {'age': 61}}
    """
    cleaned = {}

    if isinstance(nested, dict):
        for key, value in nested.items():
            if not (isinstance(key, str) and key.startswith("_")):
                cleaned[key] = delete_private_keys(value)
    else:
        cleaned = nested

    return cleaned


def flatten(
    nested: dict,
    prev_key: tuple = (),
    max_depth: int | None = None,
) -> dict:
    """Flatten ``nested`` dict by creating key tuples for each value at ``max_depth``.

    >>> nested = {"tumor": {"1": {"t_stage": 1, "size": 12.3}}}
    >>> flatten(nested)
    {('tumor', '1', 't_stage'): 1, ('tumor', '1', 'size'): 12.3}
    >>> mapping = {"patient": {"#": {"age": {"func": int, "columns": ["age"]}}}}
    >>> flatten(mapping, max_depth=3)
    {('patient', '#', 'age'): {'func': <class 'int'>, 'columns': ['age']}}

    Note that flattening an already flat dictionary will yield some weird results.
    """
    result = {}

    for key, value in nested.items():
        is_dict = isinstance(value, dict)
        has_reached_max_depth = max_depth is not None and len(prev_key) >= max_depth - 1

        if is_dict and not has_reached_max_depth:
            result.update(flatten(value, (*prev_key, key), max_depth))
        else:
            result[(*prev_key, key)] = value

    return result


def unflatten(flat: dict) -> dict:
    """Take a flat dictionary with tuples of keys and create nested dict from it.

    >>> flat = {('tumor', '1', 't_stage'): 1, ('tumor', '1', 'size'): 12.3}
    >>> unflatten(flat)
    {'tumor': {'1': {'t_stage': 1, 'size': 12.3}}}
    >>> mapping = {('patient', '#', 'age'): {'func': int, 'columns': ['age']}}
    >>> unflatten(mapping)
    {'patient': {'#': {'age': {'func': <class 'int'>, 'columns': ['age']}}}}
    """
    result = {}

    for keys, value in flat.items():
        current = result
        for key in keys[:-1]:
            current = current.setdefault(key, {})

        current[keys[-1]] = value

    return result


def get_depth(
    nested_map: dict,
    leaf_keys: set | None = None,
) -> int:
    """Get the depth at which 'leaf' dicts sit in a nested dictionary.

    A leaf is a dictionary that contains any of the ``leaf_keys``. The default is
    ``{"func", "default"}``.

    >>> nested_column_map = {"patient": {"age": {"func": int}}}
    >>> get_depth(nested_column_map)
    2
    >>> flat_column_map = flatten(nested_column_map, max_depth=2)
    >>> get_depth(flat_column_map)
    1
    >>> nested_column_map = {"patient": {"__doc__": "some patient info", "age": 61}}
    >>> get_depth(nested_column_map)   # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    ValueError: Leaf of nested map must be dict with any of ['default', 'func'].
    """
    leaf_keys = leaf_keys or {"func", "default"}

    for _, value in nested_map.items():
        if not isinstance(value, dict):
            raise ValueError(
                f"Leaf of nested map must be dict with any of {sorted(leaf_keys)}."
            )

        is_leaf = not set(value.keys()).isdisjoint(leaf_keys)
        return 1 if is_leaf else 1 + get_depth(value, leaf_keys)

    raise ValueError("Empty `nested_map`.")


def transform_to_lyprox(
    raw: pd.DataFrame,
    column_map: dict[str | tuple, dict | Any],
) -> pd.DataFrame:
    """Transform ``raw`` data into table that can be uploaded directly to `LyProX`_.

    To do so, it uses instructions in the ``colum_map`` dictionary, that needs to have
    a particular structure:

    For each column in the final 'lyproxified' :py:class:`pd.DataFrame`, one entry must
    exist in the ``column_map`` dictionary. E.g., for the column corresponding to a
    patient's age, the dictionary should contain a key-value pair of this shape:

    .. code-block:: python

        column_map = {
            ("patient", "#", "age"): {
                "func": compute_age_from_raw,
                "kwargs": {"randomize": False},
                "columns": ["birthday", "date of diagnosis"]
            },
        }

    In this example, the function ``compute_age_from_raw`` is called with the
    values of the columns ``"birthday"`` and ``"date of diagnosis"`` as positional
    arguments, and the keyword argument ``"randomize"`` is set to ``False``. The
    function then returns the patient's age, which is subsequently stored in the column
    ``("patient", "#", "age")``.

    Alternatively, this dictionary can also have a nested, tree-like structure, like
    this:

    .. code-block:: python

        column_map = {
            "patient": {
                "#": {
                    "age": {
                        "func": compute_age_from_raw,
                        "kwargs": {"randomize": False},
                        "columns": ["birthday", "date of diagnosis"]
                    }
                }
            }
        }

    In this case it is imortant that all the leaf nodes, which are defined by having
    either a ``"func"`` or a ``"default"`` key, are at the same depth. Because this
    nested dictionary is flattened to look like the first example above.

    .. _LyProX: https://lyprox.org
    """
    column_map = delete_private_keys(column_map)
    instruction_depth = get_depth(column_map)

    if instruction_depth > 1:
        column_map = flatten(column_map, max_depth=instruction_depth)

    multi_idx = pd.MultiIndex.from_tuples(column_map.keys())
    processed = pd.DataFrame(columns=multi_idx)

    for multi_idx_col, instruction in column_map.items():
        if instruction == "":
            continue

        if "default" in instruction:
            processed[multi_idx_col] = [instruction["default"]] * len(raw)

        elif "func" in instruction:
            cols = instruction.get("columns", [])
            kwargs = instruction.get("kwargs", {})
            func = instruction["func"]

            try:
                processed[multi_idx_col] = [
                    func(*vals, **kwargs) for vals in raw[cols].values
                ]
            except Exception as exc:
                raise ParsingError(
                    f"Exception encountered while parsing column {multi_idx_col}"
                ) from exc

        else:
            raise ParsingError(
                f"Column {multi_idx_col} has neither a `default` value nor `func` "
                "describing how to fill this column."
            )

    return processed


if __name__ == "__main__":
    validate_datasets()
