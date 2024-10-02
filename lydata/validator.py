"""Module to validate the CSV schema of the lydata datasets.

Here we define the function :py:func:`construct_schema` to dynamically create a
:py:class:`pandera.DataFrameSchema` that we can use to validate that a given
:py:class:`~pandas.DataFrame` conforms to the minimum requirements of the lyDATA
datasets.

For now, we only publish the :py:func:`validate_datasets` function that validates all
datasets that are found by the function :py:func:`~lydata.loader.available_datasets`.
In the future, we may want to make this more flexible.
"""

import logging

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


if __name__ == "__main__":
    validate_datasets()
