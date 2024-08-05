"""Module to validate the CSV schema of the lydata datasets."""

from pandera import Check, Column, DataFrameSchema
from pandera.errors import SchemaError

from lydata.loader import available_datasets

_NULLABLE_OPTIONAL = {"required": False, "nullable": True}
_NULLABLE_OPTIONAL_BOOLEAN_COLUMN = Column(
    dtype="boolean",
    coerce=True,
    **_NULLABLE_OPTIONAL,
)
_DATE_CHECK = Check.str_matches(r"^\d{4}-\d{2}-\d{2}$")
_LNLS = [
    "I", "Ia", "Ib",
    "II", "IIa", "IIb",
    "III",
    "IV",
    "V", "Va", "Vb",
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
    ("patient", "#", "weight"): Column(float, Check.greater_than(0), **_NULLABLE_OPTIONAL),
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
    ("tumor", "1", "volume"): Column(float, Check.greater_than(0), **_NULLABLE_OPTIONAL),
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
    """Construct a DataFrameSchema for the lydata datasets."""
    schema = DataFrameSchema(patient_columns).add_columns(tumor_columns)

    for modality in modalities:
        schema = schema.add_columns(get_modality_columns(modality, lnls))

    return schema


def validate() -> None:
    """Validate all lydata datasets."""
    lydata_schema = construct_schema(
        modalities=["pathology", "diagnostic_consensus", "PET", "CT", "FNA", "MRI"],
    )

    for data_spec in available_datasets():
        dataset = data_spec.load()
        try:
            lydata_schema.validate(dataset)
        except SchemaError as schema_err:
            raise Exception(
                f"Schema validation failed for {data_spec!r}."
            ) from schema_err


if __name__ == "__main__":
    validate()
