"""Utility functions and classes."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field


@dataclass
class _ColumnSpec:
    """Class for specifying column names and aggfuncs."""

    short: str
    long: tuple[str, str, str]
    agg_func: str | Callable[[pd.Series], pd.Series] = "value_counts"
    agg_kwargs: dict[str, Any] = field(default_factory=lambda: {"dropna": False})

    def __call__(self, series: pd.Series) -> pd.Series:
        """Call the aggregation function on the series."""
        return series.agg(self.agg_func, **self.agg_kwargs)


@dataclass
class _ColumnMap:
    """Class for mapping short and long column names."""

    from_short: dict[str, _ColumnSpec]
    from_long: dict[tuple[str, str, str], _ColumnSpec]

    def __post_init__(self) -> None:
        """Check ``from_short`` and ``from_long`` contain same ``_ColumnSpec``."""
        for left, right in zip(
            self.from_short.values(), self.from_long.values(), strict=True
        ):
            if left != right:
                raise ValueError(
                    "`from_short` and `from_long` contain different "
                    "`_ColumnSpec` instances"
                )

    @classmethod
    def from_list(cls, columns: list[_ColumnSpec]) -> "_ColumnMap":
        """Create a ColumnMap from a list of ColumnSpecs."""
        short = {col.short: col for col in columns}
        long = {col.long: col for col in columns}
        return cls(short, long)

    def __iter__(self):
        """Iterate over the short names."""
        return iter(self.from_short.values())


def get_default_column_map() -> _ColumnMap:
    """Get the default column map."""
    return _ColumnMap.from_list(
        [
            _ColumnSpec("age", ("patient", "#", "age")),
            _ColumnSpec("hpv", ("patient", "#", "hpv_status")),
            _ColumnSpec("smoke", ("patient", "#", "nicotine_abuse")),
            _ColumnSpec("alcohol", ("patient", "#", "alcohol_abuse")),
            _ColumnSpec("t_stage", ("tumor", "1", "t_stage")),
            _ColumnSpec("n_stage", ("patient", "#", "n_stage")),
            _ColumnSpec("m_stage", ("patient", "#", "m_stage")),
            _ColumnSpec("midext", ("tumor", "1", "extension")),
        ]
    )


class ModalityConfig(BaseModel):
    """Define a diagnostic or pathological modality."""

    spec: float = Field(ge=0.5, le=1.0, description="Specificity of the modality.")
    sens: float = Field(ge=0.5, le=1.0, description="Sensitivity of the modality.")
    kind: Literal["clinical", "pathological"] = Field(
        default="clinical",
        description="Clinical modalities cannot detect microscopic disease.",
    )


def get_default_modalities() -> list[ModalityConfig]:
    """Get defaults values for sensitivities and specificities of modalities.

    Taken from [de Bondt et al. (2007)](https://doi.org/10.1016/j.ejrad.2007.02.037)
    and [Kyzas et al. (2008)](https://doi.org/10.1093/jnci/djn125).
    """
    return [
        ModalityConfig("CT", 0.76, 0.81),
        ModalityConfig("MRI", 0.63, 0.81),
        ModalityConfig("PET", 0.86, 0.79),
        ModalityConfig("FNA", 0.98, 0.80, "pathological"),
        ModalityConfig("diagnostic_consensus", 0.86, 0.81),
        ModalityConfig("pathology", 1.0, 1.0, "pathological"),
        ModalityConfig("pCT", 0.86, 0.81),
    ]


def main() -> None:
    """Run the main function."""
    ...


if __name__ == "__main__":
    main()
