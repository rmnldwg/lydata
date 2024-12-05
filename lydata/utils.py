"""Utility functions and classes."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field


def update_and_expand(
    left: pd.DataFrame,
    right: pd.DataFrame,
    **update_kwargs: Any,
) -> pd.DataFrame:
    """Update ``left`` with values from ``right``, also adding .

    The added feature of this function over pandas' :py:meth:`~pandas.DataFrame.update`
    is that it also adds columns that are present in ``right`` but not in ``left``.

    Any keyword arguments are also directly passed to the
    :py:meth:`~pandas.DataFrame.update`.

    >>> left = pd.DataFrame({"a": [1, 2, None], "b": [3, 4, 5]})
    >>> right = pd.DataFrame({"a": [None, 3, 4], "c": [6, 7, 8]})
    >>> update_and_expand(left, right)
         a  b  c
    0  1.0  3  6
    1  3.0  4  7
    2  4.0  5  8
    """
    result = left.copy()
    result.update(right, **update_kwargs)

    for column in right.columns:
        if column not in result.columns:
            result[column] = right[column]

    return result


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
    """Get the default column map.

    This map defines which short column names can be used to access columns in the
    DataFrames.

    >>> from lydata import accessor, loader
    >>> df = next(loader.load_datasets(institution="usz"))
    >>> df.ly.surgery   # doctest: +ELLIPSIS
    0      False
    ...
    286    False
    Name: (patient, #, neck_dissection), Length: 287, dtype: bool
    >>> df.ly.smoke   # doctest: +ELLIPSIS
    0       True
    ...
    286     True
    Name: (patient, #, nicotine_abuse), Length: 287, dtype: bool
    """
    return _ColumnMap.from_list(
        [
            _ColumnSpec("id", ("patient", "#", "id")),
            _ColumnSpec("institution", ("patient", "#", "institution")),
            _ColumnSpec("sex", ("patient", "#", "sex")),
            _ColumnSpec("age", ("patient", "#", "age")),
            _ColumnSpec("weight", ("patient", "#", "weight")),
            _ColumnSpec("date", ("patient", "#", "diagnose_date")),
            _ColumnSpec("surgery", ("patient", "#", "neck_dissection")),
            _ColumnSpec("hpv", ("patient", "#", "hpv_status")),
            _ColumnSpec("smoke", ("patient", "#", "nicotine_abuse")),
            _ColumnSpec("alcohol", ("patient", "#", "alcohol_abuse")),
            _ColumnSpec("t_stage", ("tumor", "1", "t_stage")),
            _ColumnSpec("n_stage", ("patient", "#", "n_stage")),
            _ColumnSpec("m_stage", ("patient", "#", "m_stage")),
            _ColumnSpec("midext", ("tumor", "1", "extension")),
            _ColumnSpec("subsite", ("tumor", "1", "subsite")),
            _ColumnSpec("volume", ("tumor", "1", "volume")),
            _ColumnSpec("central", ("tumor", "1", "central")),
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


def get_default_modalities() -> dict[str, ModalityConfig]:
    """Get defaults values for sensitivities and specificities of modalities.

    Taken from `de Bondt et al. (2007) <https://doi.org/10.1016/j.ejrad.2007.02.037>`_
    and `Kyzas et al. (2008) <https://doi.org/10.1093/jnci/djn125>`_.
    """
    return {
        "CT": ModalityConfig(spec=0.76, sens=0.81),
        "MRI": ModalityConfig(spec=0.63, sens=0.81),
        "PET": ModalityConfig(spec=0.86, sens=0.79),
        "FNA": ModalityConfig(spec=0.98, sens=0.80, kind="pathological"),
        "diagnostic_consensus": ModalityConfig(spec=0.86, sens=0.81),
        "pathology": ModalityConfig(spec=1.0, sens=1.0, kind="pathological"),
        "pCT": ModalityConfig(spec=0.86, sens=0.81),
    }


def infer_all_levels(
    dataset: pd.DataFrame,
    infer_superlevels_kwargs: dict[str, Any] | None = None,
    infer_sublevels_kwargs: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Infer all levels of involvement for each diagnostic modality.

    This function first infers sublevel (e.g. 'IIa', and 'IIb') involvement for each
    modality using :py:meth:`~lydata.accessor.LyDataAccessor.infer_sublevels`. Then,
    it infers superlevel (e.g. 'II') involvement for each modality using
    :py:meth:`~lydata.accessor.LyDataAccessor.infer_superlevels`.
    """
    infer_sublevels_kwargs = infer_sublevels_kwargs or {}
    infer_superlevels_kwargs = infer_superlevels_kwargs or {}

    result = dataset.copy()

    result = update_and_expand(
        left=result,
        right=result.ly.infer_superlevels(**infer_superlevels_kwargs),
    )
    return update_and_expand(
        left=result,
        right=result.ly.infer_sublevels(**infer_sublevels_kwargs),
    )


def infer_and_combine_levels(
    dataset: pd.DataFrame,
    infer_superlevels_kwargs: dict[str, Any] | None = None,
    infer_sublevels_kwargs: dict[str, Any] | None = None,
    combine_kwargs: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Enhance the dataset by inferring additional columns from the data.

    This performs the following steps in order:

    1. Infer the superlevel involvement for each diagnostic modality using the
        :py:meth:`~lydata.accessor.LyDataAccessor.infer_superlevels` method.
    2. Infer the sublevel involvement for each diagnostic modality using the
        :py:meth:`~lydata.accessor.LyDataAccessor.infer_sublevels` method. This skips
        all LNLs that were computed in the previous step.
    3. Compute the maximum likelihood estimate of the true state of the patient using
        the :py:meth:`~lydata.accessor.LyDataAccessor.combine`.

    .. important::

        Performing these operations in any other order may lead to the loss of some
        information or even to conflicting LNL involvement information.

    The result contains all LNLs of interest in the head and neck region, as well as
    the best estimate of the true state of the patient under the top-level key
    ``max_llh``.
    """
    result = infer_all_levels(
        dataset,
        infer_superlevels_kwargs=infer_superlevels_kwargs,
        infer_sublevels_kwargs=infer_sublevels_kwargs,
    )
    combine_kwargs = combine_kwargs or {}
    max_llh = pd.concat(
        {"max_llh": result.ly.combine(**combine_kwargs)},
        axis="columns",
    )
    return result.join(max_llh)


def _main() -> None:
    """Run the main function."""
    ...


if __name__ == "__main__":
    _main()
