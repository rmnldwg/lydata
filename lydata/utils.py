"""Utility functions and classes."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


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

    @classmethod
    def from_list(cls, columns: list[_ColumnSpec]) -> "_ColumnMap":
        """Create a ColumnMap from a list of ColumnSpecs."""
        short = {col.short: col for col in columns}
        long = {col.long: col for col in columns}
        return cls(short, long)

    def __iter__(self):
        """Iterate over the short names."""
        return iter(self.from_short.values())


_COLUMN_MAP = _ColumnMap.from_list([
    _ColumnSpec("age", ("patient", "#", "age")),
    _ColumnSpec("hpv", ("patient", "#", "hpv_status")),
    _ColumnSpec("smoke", ("patient", "#", "nicotine_abuse")),
    _ColumnSpec("alcohol", ("patient", "#", "alcohol_abuse")),
    _ColumnSpec("t_stage", ("tumor"  , "1", "t_stage")),
    _ColumnSpec("n_stage", ("patient", "#", "n_stage")),
    _ColumnSpec("m_stage", ("patient", "#", "m_stage")),
    _ColumnSpec("midext", ("tumor"  , "1", "extension")),
])


def main() -> None:
    """Run the main function."""
    for col in _COLUMN_MAP:
        print(col)


if __name__ == "__main__":
    main()
