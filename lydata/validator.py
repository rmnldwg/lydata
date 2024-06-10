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


lydata_schema = DataFrameSchema({
    ("patient", "#", "institution"): Column(str),
    ("patient", "#", "sex"): Column(str, Check.str_matches(r"^(male|female)$")),
    ("patient", "#", "age"): Column(int),
    ("patient", "#", "weight"): Column(float, Check.greater_than(0), **_NULLABLE_OPTIONAL),
    ("patient", "#", "diagnose_date"): Column(str, Check.str_matches(r"^\d{4}-\d{2}-\d{2}$")),
    ("patient", "#", "alcohol_abuse"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
    ("patient", "#", "nicotine_abuse"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
    ("patient", "#", "hpv_status"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
    ("patient", "#", "neck_dissection"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
    ("patient", "#", "tnm_edition"): Column(int, Check.in_range(7, 8)),
    ("patient", "#", "n_stage"): Column(int, Check.in_range(0, 3)),
    ("patient", "#", "m_stage"): Column(int, Check.in_range(-1, 1)),

    ("tumor", "1", "subsite"): Column(str, Check.str_matches(r"^C\d{2}(\.\d)?$")),
    ("tumor", "1", "t_stage"): Column(int, Check.in_range(0, 4)),
    ("tumor", "1", "stage_prefix"): Column(str, Check.str_matches(r"^(p|c)$")),
    ("tumor", "1", "volume"): Column(float, Check.greater_than(0), **_NULLABLE_OPTIONAL),
    ("tumor", "1", "central"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
    ("tumor", "1", "extension"): _NULLABLE_OPTIONAL_BOOLEAN_COLUMN,
})


def validate() -> None:
    """Validate some lydata datasets."""
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
