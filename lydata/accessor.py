"""Module containing a custom accessor and helpers for querying lyDATA.

Because of the special three-level header of the lyDATA tables, it is sometimes
cumbersome and lengthy to access the columns. While this is certainly necessary to
access e.g. the contralateral involvement of LNL II as observed on CT images
(``df["CT", "contra", "II"]``), for simple patient information such as age and HPV
status, it is more convenient to use short names, which we implement in this module.

The main class in this module is the :py:class:`LyDataAccessor` class, which provides
the above mentioned functionality. That way, accessing the age of all patients is now
as easy as typing ``df.ly.age``.

Beyond that, the module implements a convenient wat to query the
:py:class:`pd.DataFrame`: The :py:class:`Q` object, that was inspired by Django's
``Q`` object. It allows for more readable and modular queries, which can be combined
with logical operators and reused across different DataFrames.

The :py:class:`Q` objects can be passed to the :py:meth:`LyDataAccessor.query` and
:py:meth:`LyDataAccessor.portion` methods to filter the DataFrame or compute the
:py:class:`QueryPortion` of rows that satisfy the query.

Further, we implement methods like :py:meth:`LyDataAccessor.combine`,
:py:meth:`LyDataAccessor.infer_sublevels`, and
:py:meth:`LyDataAccessor.infer_superlevels` to compute additional columns from the
lyDATA tables. This is sometimes necessary, because not all data contains all the
possibly necessary columns. E.g., in some cohorts we do have detailed sublevel
information (i.e., IIa and IIb), while in others only the superlevel (II) is reported.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass
from itertools import product
from typing import Any, Literal

import numpy as np
import pandas as pd
import pandas.api.extensions as pd_ext

from lydata.utils import (
    ModalityConfig,
    get_default_column_map,
    get_default_modalities,
)
from lydata.validator import construct_schema


def _get_all_true(df: pd.DataFrame) -> pd.Series:
    """Return a mask with all entries set to ``True``."""
    return pd.Series([True] * len(df))


class CombineQMixin:
    """Mixin class for combining queries."""

    def __and__(self, other: QTypes) -> AndQ:
        """Combine two queries with a logical AND."""
        return AndQ(self, other)

    def __or__(self, other: QTypes) -> OrQ:
        """Combine two queries with a logical OR."""
        return OrQ(self, other)

    def __invert__(self) -> NotQ:
        """Negate the query."""
        return NotQ(self)


class Q(CombineQMixin):
    """Combinable query object for filtering a DataFrame.

    The syntax for this object is similar to Django's ``Q`` object. It can be used to
    define queries in a more readable and modular way.

    .. caution::

        The column names are not checked upon instantiation. This is only done when the
        query is executed. In fact, the ``Q`` object does not even know about the
        :py:class:`~pandas.DataFrame` it will be applied to in the beginning. On the
        flip side, this means a query may be reused for different DataFrames.
    """

    _OPERATOR_MAP: dict[str, Callable[[pd.Series, Any], pd.Series]] = {
        "==": lambda series, value: series == value,
        "<": lambda series, value: series < value,
        "<=": lambda series, value: series <= value,
        ">": lambda series, value: series > value,
        ">=": lambda series, value: series >= value,
        "!=": lambda series, value: series != value,  # same as ~Q("col", "==", value)
        "in": lambda series, value: series.isin(value),  # value is a list
    }

    def __init__(
        self,
        column: str,
        operator: Literal["==", "<", "<=", ">", ">=", "!=", "in"],
        value: Any,
    ) -> None:
        """Create query object that can compare a ``column`` with a ``value``."""
        self.colname = column
        self.operator = operator
        self.value = value
        self._column_map = get_default_column_map()

    def __repr__(self) -> str:
        """Return a string representation of the query."""
        return f"Q({self.colname!r}, {self.operator!r}, {self.value!r})"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask where the query is satisfied for ``df``."""
        try:
            colname = self._column_map.from_short[self.colname].long
        except KeyError:
            colname = self.colname

        column = df[colname]

        if callable(self.value):
            return self.value(column)

        return self._OPERATOR_MAP[self.operator](column, self.value)


class AndQ(CombineQMixin):
    """Query object for combining two queries with a logical AND.

    >>> df = pd.DataFrame({'col1': [1, 2, 3]})
    >>> q1 = Q('col1', '>', 1)
    >>> q2 = Q('col1', '<', 3)
    >>> and_q = q1 & q2
    >>> print(and_q)
    Q('col1', '>', 1) & Q('col1', '<', 3)
    >>> isinstance(and_q, AndQ)
    True
    >>> and_q.execute(df)
    0    False
    1     True
    2    False
    Name: col1, dtype: bool
    """

    def __init__(self, q1: QTypes, q2: QTypes) -> None:
        """Combine two queries with a logical AND."""
        self.q1 = q1
        self.q2 = q2

    def __repr__(self) -> str:
        """Return a string representation of the query."""
        return f"{self.q1!r} & {self.q2!r}"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask where both queries are satisfied."""
        return self.q1.execute(df) & self.q2.execute(df)


class OrQ(CombineQMixin):
    """Query object for combining two queries with a logical OR.

    >>> df = pd.DataFrame({'col1': [1, 2, 3]})
    >>> q1 = Q('col1', '==', 1)
    >>> q2 = Q('col1', '==', 3)
    >>> or_q = q1 | q2
    >>> print(or_q)
    Q('col1', '==', 1) | Q('col1', '==', 3)
    >>> isinstance(or_q, OrQ)
    True
    >>> or_q.execute(df)
    0     True
    1    False
    2     True
    Name: col1, dtype: bool
    """

    def __init__(self, q1: QTypes, q2: QTypes) -> None:
        """Combine two queries with a logical OR."""
        self.q1 = q1
        self.q2 = q2

    def __repr__(self) -> str:
        """Return a string representation of the query."""
        return f"{self.q1!r} | {self.q2!r}"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask where either query is satisfied."""
        return self.q1.execute(df) | self.q2.execute(df)


class NotQ(CombineQMixin):
    """Query object for negating a query.

    >>> df = pd.DataFrame({'col1': [1, 2, 3]})
    >>> q = Q('col1', '==', 2)
    >>> not_q = ~q
    >>> print(not_q)
    ~Q('col1', '==', 2)
    >>> isinstance(not_q, NotQ)
    True
    >>> not_q.execute(df)
    0     True
    1    False
    2     True
    Name: col1, dtype: bool
    """

    def __init__(self, q: QTypes) -> None:
        """Negate the given query ``q``."""
        self.q = q

    def __repr__(self) -> str:
        """Return a string representation of the query."""
        return f"~{self.q!r}"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask where the query is not satisfied."""
        return ~self.q.execute(df)


class NoneQ(CombineQMixin):
    """Query object that always returns the entire DataFrame. Useful as default."""

    def __repr__(self) -> str:
        """Return a string representation of the query."""
        return "NoneQ()"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask with all entries set to ``True``."""
        return _get_all_true(df)


QTypes = Q | AndQ | OrQ | NotQ | None


class C:
    """Wraps a column name and produces a :py:class:`Q` object upon comparison.

    .. caution::

        Just like for the :py:class:`Q` object, it is not checked upon instantiation
        whether the column name is valid. This is only done when the query is executed.
    """

    def __init__(self, column: str) -> None:
        """Create a column object for comparison."""
        self.column = column

    def __eq__(self, value: Any) -> Q:
        """Create a query object for comparing equality.

        >>> C('foo') == 'bar'
        Q('foo', '==', 'bar')
        """
        return Q(self.column, "==", value)

    def __lt__(self, value: Any) -> Q:
        """Create a query object for comparing less than.

        >>> C('foo') < 42
        Q('foo', '<', 42)
        """
        return Q(self.column, "<", value)

    def __le__(self, value: Any) -> Q:
        """Create a query object for comparing less than or equal.

        >>> C('foo') <= 42
        Q('foo', '<=', 42)
        """
        return Q(self.column, "<=", value)

    def __gt__(self, value: Any) -> Q:
        """Create a query object for comparing greater than.

        >>> C('foo') > 42
        Q('foo', '>', 42)
        """
        return Q(self.column, ">", value)

    def __ge__(self, value: Any) -> Q:
        """Create a query object for comparing greater than or equal.

        >>> C('foo') >= 42
        Q('foo', '>=', 42)
        """
        return Q(self.column, ">=", value)

    def __ne__(self, value: Any) -> Q:
        """Create a query object for comparing inequality.

        >>> C('foo') != 'bar'
        Q('foo', '!=', 'bar')
        """
        return Q(self.column, "!=", value)

    def in_(self, value: list[Any]) -> Q:
        """Create a query object for checking if the column values are in a list.

        >>> C('foo').in_([1, 2, 3])
        Q('foo', 'in', [1, 2, 3])
        """
        return Q(self.column, "in", value)


@dataclass
class QueryPortion:
    """Dataclass for storing the portion of a query."""

    match: int
    total: int

    def __post_init__(self) -> None:
        """Check that the portion is valid.

        >>> QueryPortion(5, 2)
        Traceback (most recent call last):
            ...
        ValueError: Match must be less than or equal to total.
        """
        if self.total < 0:
            raise ValueError("Total must be non-negative.")
        if self.match < 0:
            raise ValueError("Match must be non-negative.")
        if self.match > self.total:
            raise ValueError("Match must be less than or equal to total.")

    @property
    def fail(self) -> int:
        """Get the number of failures.

        >>> QueryPortion(2, 5).fail
        3
        """
        return self.total - self.match

    @property
    def ratio(self) -> float:
        """Get the ratio of matches over the total.

        >>> QueryPortion(2, 5).ratio
        0.4
        """
        return self.match / self.total

    @property
    def percent(self) -> float:
        """Get the percentage of matches over the total.

        >>> QueryPortion(2, 5).percent
        40.0
        """
        return self.ratio * 100

    def invert(self) -> QueryPortion:
        """Return the inverted portion.

        >>> QueryPortion(2, 5).invert()
        QueryPortion(match=3, total=5)
        """
        return QueryPortion(match=self.fail, total=self.total)


def align_diagnoses(
    dataset: pd.DataFrame,
    modalities: list[str],
) -> list[pd.DataFrame]:
    """Stack aligned diagnosis tables in ``dataset`` for each of ``modalities``."""
    diagnosis_stack = []
    for modality in modalities:
        try:
            this = dataset[modality].copy().drop(columns=["info"], errors="ignore")
        except KeyError:
            warnings.warn(f"Did not find modality {modality}, cannot align. Skipping.")  # noqa
            continue

        for i, other in enumerate(diagnosis_stack):
            this, other = this.align(other, join="outer")
            diagnosis_stack[i] = other

        diagnosis_stack.append(this)

    return diagnosis_stack


def _create_raising_func(method: str):
    """Raise ValueError for wrong ``method``."""

    def raise_value_err(*args, **kwargs):
        raise ValueError(f"Unknown method {method}")

    return raise_value_err


def _false_estimate(
    obs: np.ndarray,
    false_pos_probs: np.ndarray,
    true_neg_probs: np.ndarray,
    method: Literal["prod", "max"],
) -> float:
    """Compute estimate of ``False``, given ``obs``.

    >>> _false_estimate([True, False], [0.1, 0.6], [0.4, 0.7], method="whatever")
    Traceback (most recent call last):
        ...
    ValueError: Unknown method whatever
    """
    false_llhs = np.where(obs, false_pos_probs, true_neg_probs)
    nans_masked = np.where(
        pd.isna(obs),
        1.0 if method == "prod" else 0.0,
        false_llhs,
    )
    method = getattr(np, method, _create_raising_func(method))
    return method(nans_masked)


def _true_estimate(
    obs: np.ndarray,
    true_pos_probs: np.ndarray,
    false_neg_probs: np.ndarray,
    method: Literal["prod", "max"],
) -> float:
    """Compute estimate of ``True``, given ``obs``.

    >>> obs = [True, False, np.nan]
    >>> true_pos_probs = [0.8, 0.6, 0.9]
    >>> false_neg_probs = [0.6, 0.7, 0.9]
    >>> _true_estimate(obs, true_pos_probs, false_neg_probs, method="max")
    np.float64(0.8)
    >>> tmp = _true_estimate(obs, true_pos_probs, false_neg_probs, method="prod")
    >>> np.isclose(tmp, 0.56)
    np.True_
    """
    true_llhs = np.where(obs, true_pos_probs, false_neg_probs)
    nans_masked = np.where(
        pd.isna(obs),
        1.0 if method == "prod" else 0.0,
        true_llhs,
    )
    method = getattr(np, method, _create_raising_func(method))
    return method(nans_masked)


def _max_likelihood(
    obs: np.ndarray,
    specificities: np.ndarray,
    sensitivities: np.ndarray,
) -> bool:
    """Compute most likely true state based on all ``obs``.

    >>> obs = np.array([True, False, np.nan, None])
    >>> sensitivities = np.array([0.9, 0.7, 0.7, 0.7])
    >>> specificities = np.array([0.9, 0.7, 0.7, 0.7])
    >>> _max_likelihood(obs, sensitivities, specificities)
    np.True_
    >>> obs = np.array([True, False, False, False])
    >>> _max_likelihood(obs, sensitivities, specificities)
    np.False_
    """
    healthy_llh = _false_estimate(obs, 1 - specificities, specificities, method="prod")
    involved_llhs = _true_estimate(obs, sensitivities, 1 - sensitivities, method="prod")
    return healthy_llh < involved_llhs


def _rank_trustworthy(
    obs: np.ndarray,
    specificities: np.ndarray,
    sensitivities: np.ndarray,
) -> bool:
    """Estimate true state based on most trustworthy value in ``obs``.

    >>> obs = np.array([True, False, np.nan, None])
    >>> sensitivities = np.array([0.9, 0.7, 0.7, 0.7])
    >>> specificities = np.array([0.9, 0.7, 0.7, 0.7])
    >>> _rank_trustworthy(obs, sensitivities, specificities)
    np.True_
    >>> obs = np.array([True, False, False, False])
    >>> _rank_trustworthy(obs, sensitivities, specificities)
    np.True_
    """
    healthy_llh = _false_estimate(obs, 1 - specificities, specificities, method="max")
    involved_llhs = _true_estimate(obs, sensitivities, 1 - sensitivities, method="max")
    return healthy_llh < involved_llhs


def _expand_mapping(
    short_map: dict[str, Any],
    colname_map: dict[str | tuple[str, str, str], Any] | None = None,
) -> dict[tuple[str, str, str], Any]:
    """Expand the column map to full column names.

    >>> _expand_mapping({'age': 'foo', 'hpv': 'bar'})
    {('patient', '#', 'age'): 'foo', ('patient', '#', 'hpv_status'): 'bar'}
    """
    _colname_map = colname_map or get_default_column_map().from_short
    expanded_map = {}

    for colname, func in short_map.items():
        expanded_colname = getattr(_colname_map.get(colname), "long", colname)
        expanded_map[expanded_colname] = func

    return expanded_map


AggFuncType = dict[str | tuple[str, str, str], Callable[[pd.Series], pd.Series]]


@pd_ext.register_dataframe_accessor("ly")
class LyDataAccessor:
    """Custom accessor for handling lymphatic involvement data.

    This aims to provide an easy and user-friendly interface to the most commonly needed
    operations on the lymphatic involvement data we publish in the lydata project.
    """

    def __init__(self, obj: pd.DataFrame) -> None:
        """Initialize the accessor with a DataFrame."""
        self._obj = obj
        self._column_map = get_default_column_map()

    def __contains__(self, key: str) -> bool:
        """Check if a column is contained in the DataFrame.

        >>> df = pd.DataFrame({("patient", "#", "age"): [61, 52, 73]})
        >>> "age" in df.ly
        True
        >>> "foo" in df.ly
        False
        >>> ("patient", "#", "age") in df.ly
        True
        """
        _key = self._get_safe_long(key)
        return _key in self._obj

    def __getitem__(self, key: str) -> pd.Series:
        """Allow column access by short name, too."""
        _key = self._get_safe_long(key)
        return self._obj[_key]

    def __getattr__(self, name: str) -> Any:
        """Access columns also by short name.

        >>> df = pd.DataFrame({("patient", "#", "age"): [61, 52, 73]})
        >>> df.ly.age
        0    61
        1    52
        2    73
        Name: (patient, #, age), dtype: int64
        >>> df.ly.foo
        Traceback (most recent call last):
            ...
        AttributeError: Attribute 'foo' not found.
        """
        try:
            return self[name]
        except KeyError as key_err:
            raise AttributeError(f"Attribute {name!r} not found.") from key_err

    def _get_safe_long(self, key: Any) -> tuple[str, str, str]:
        """Get the long column name or return the input."""
        return getattr(self._column_map.from_short.get(key), "long", key)

    def validate(self, modalities: list[str] | None = None) -> pd.DataFrame:
        """Validate the DataFrame against the lydata schema.

        The schema is constructed by the :py:func:`construct_schema` function using
        the ``modalities`` provided or it will :py:func:`get_default_modalities` if
        ``None`` are provided.
        """
        modalities = modalities or list(get_default_modalities().keys())
        lydata_schema = construct_schema(modalities=modalities)
        return lydata_schema.validate(self._obj)

    def get_modalities(self, _filter: list[str] | None = None) -> list[str]:
        """Return the modalities present in this DataFrame.

        .. warning::

            This method assumes that all top-level columns are modalities, except for
            some predefined non-modality columns. For some custom dataset, this may not
            be correct. In that case, you should provide a list of columns to
            ``_filter``, i.e., the columns that are *not* modalities.
        """
        top_level_cols = self._obj.columns.get_level_values(0)
        modalities = top_level_cols.unique().tolist()

        for non_modality_col in _filter or [
            "patient",
            "tumor",
            "total_dissected",
            "positive_dissected",
            "enbloc_dissected",
            "enbloc_positive",
        ]:
            try:
                modalities.remove(non_modality_col)
            except ValueError:
                pass

        return modalities

    def query(self, query: QTypes = None) -> pd.DataFrame:
        """Return a DataFrame with rows that satisfy the ``query``.

        A query is a :py:class:`Q` object that can be combined with logical operators.
        See this class' documentation for more information.

        As a shorthand for creating these :py:class:`Q` objects, you can use the
        :py:class:`C` object as in the example below, where we query all entries where
        ``x`` is greater than 1 and not less than 3:

        >>> df = pd.DataFrame({'x': [1, 2, 3]})
        >>> df.ly.query((C('x') > 1) & ~(C('x') < 3))
           x
        2  3
        """
        mask = (query or NoneQ()).execute(self._obj)
        return self._obj[mask]

    def portion(self, query: QTypes = None, given: QTypes = None) -> QueryPortion:
        """Compute how many rows satisfy a ``query``, ``given`` some other conditions.

        This returns a :py:class:`QueryPortion` object that contains the number of rows
        satisfying the ``query`` and ``given`` :py:class:`Q` object divided by the
        number of rows satisfying only the ``given`` condition.

        >>> df = pd.DataFrame({'x': [1, 2, 3]})
        >>> df.ly.portion(query=C('x') ==  2, given=C('x') > 1)
        QueryPortion(match=np.int64(1), total=np.int64(2))
        >>> df.ly.portion(query=C('x') ==  2, given=C('x') > 3)
        QueryPortion(match=np.int64(0), total=np.int64(0))
        """
        given_mask = (given or NoneQ()).execute(self._obj)
        query_mask = (query or NoneQ()).execute(self._obj)

        return QueryPortion(
            match=query_mask[given_mask].sum(),
            total=given_mask.sum(),
        )

    def stats(
        self,
        agg_funcs: AggFuncType | None = None,
        use_shortnames: bool = True,
        out_format: str = "dict",
    ) -> Any:
        """Compute statistics.

        The ``agg_funcs`` argument is a mapping of column names to functions that
        receive a :py:class:`pd.Series` and return a :py:class:`pd.Series`. The default
        is a useful selection of statistics for the most common columns. E.g., for the
        column ``('patient', '#', 'age')`` (or its short column name ``age``), the
        default function returns the value counts.

        The ``use_shortnames`` argument determines whether the output should use the
        short column names or the long ones. The default is to use the short names.

        With ``out_format`` one can specify the output format. Available options are
        those formats for which pandas has a ``to_<format>`` method.

        >>> df = pd.DataFrame({
        ...     ('patient', '#', 'age'): [61, 52, 73, 61],
        ...     ('patient', '#', 'hpv_status'): [True, False, None, True],
        ...     ('tumor', '1', 't_stage'): [2, 3, 1, 2],
        ... })
        >>> df.ly.stats()   # doctest: +NORMALIZE_WHITESPACE
        {'age': {61: 2, 52: 1, 73: 1},
         'hpv': {True: 2, False: 1, None: 1},
         't_stage': {2: 2, 3: 1, 1: 1}}
        """
        _agg_funcs = self._column_map.from_short.copy()
        _agg_funcs.update(agg_funcs or {})
        stats = {}

        for colname, func in _agg_funcs.items():
            if colname not in self:
                continue

            column = self[colname]
            if use_shortnames and colname in self._column_map.from_long:
                colname = self._column_map.from_long[colname].short

            stats[colname] = getattr(func(column), f"to_{out_format}")()

        return stats

    def combine(
        self,
        modalities: dict[str, ModalityConfig] | None = None,
        method: Literal["max_llh", "rank"] = "max_llh",
    ) -> pd.DataFrame:
        """Combine diagnoses of ``modalities`` using ``method``.

        The details of what the ``method`` does and how can be found in their
        respective documentations: :py:func:`max_likelihood` and
        :py:func:`rank_trustworthy`.

        The result contains only the combined columns. The intended use is to
        :py:meth:`~pandas.DataFrame.update` the original DataFrame with the result.

        >>> df = pd.DataFrame({
        ...     ('MRI'      , 'ipsi', 'I'): [False, True , True , None],
        ...     ('CT'       , 'ipsi', 'I'): [False, True , False, True],
        ...     ('pathology', 'ipsi', 'I'): [True , None , False, None],
        ... })
        >>> df.ly.combine()   # doctest: +NORMALIZE_WHITESPACE
             ipsi
                I
        0    True
        1    True
        2   False
        3    True
        """
        modalities = modalities or get_default_modalities()
        modalities = {
            modality_name: modality_config
            for modality_name, modality_config in modalities.items()
            if modality_name in self.get_modalities()
        }

        diagnosis_stack = align_diagnoses(self._obj, list(modalities.keys()))
        columns = diagnosis_stack[0].columns
        diagnosis_stack = np.array(diagnosis_stack)

        funcs1d = {"max_llh": _max_likelihood, "rank": _rank_trustworthy}
        result = np.apply_along_axis(
            func1d=funcs1d[method],
            axis=0,
            arr=diagnosis_stack,
            sensitivities=np.array([mod.sens for mod in modalities.values()]),
            specificities=np.array([mod.spec for mod in modalities.values()]),
        )
        return pd.DataFrame(result, columns=columns)

    def infer_sublevels(
        self,
        modalities: list[str] | None = None,
        sides: list[Literal["ipsi", "contra"]] | None = None,
        subdivisions: dict[str, list[str]] | None = None,
    ) -> pd.DataFrame:
        """Determine involvement status of an LNL's sublevels (e.g., IIa and IIb).

        Some LNLs have sublevels, e.g., IIa and IIb. The involvement of these sublevels
        is not always reported, but only the superlevel's status. This function infers
        the status of the sublevels from the superlevel.

        The sublevel's status is computed for the specified ``modalities``. If and what
        sublevels a superlevel has, is specified in ``subdivisions``. The default
        ``subdivisions`` argument looks like this:

        .. code-block:: python

            {
                "I": ["a", "b"],
                "II": ["a", "b"],
                "V": ["a", "b"],
            }

        The resulting DataFrame will only contain the newly inferred sublevel columns.
        Thus, one can simply :py:meth:`~pandas.DataFrame.update` the original DataFrame
        with the result.

        >>> df = pd.DataFrame({
        ...     ('MRI', 'ipsi'  , 'I' ): [True , False, False, None],
        ...     ('MRI', 'contra', 'I' ): [False, True , False, None],
        ...     ('MRI', 'ipsi'  , 'II'): [False, False, True , None],
        ...     ('MRI', 'ipsi'  , 'IV'): [False, False, True , None],
        ...     ('CT' , 'ipsi'  , 'I' ): [True , False, False, None],
        ... })
        >>> df.ly.infer_sublevels(modalities=["MRI"])   # doctest: +NORMALIZE_WHITESPACE
             MRI
            ipsi                      contra
              Ia     Ib    IIa    IIb     Ia     Ib
        0   None   None  False  False  False  False
        1  False  False  False  False   None   None
        2  False  False   None   None  False  False
        3   None   None   None   None   None   None
        """
        modalities = modalities or list(get_default_modalities().keys())
        sides = sides or ["ipsi", "contra"]
        subdivisions = subdivisions or {
            "I": ["a", "b"],
            "II": ["a", "b"],
            "V": ["a", "b"],
        }

        result = self._obj.copy().drop(self._obj.columns, axis=1)

        loop_combinations = product(modalities, sides, subdivisions.items())
        for modality, side, (superlevel, subids) in loop_combinations:
            try:
                is_healthy = self._obj[modality, side, superlevel] == False  # noqa
            except KeyError:
                continue

            for subid in subids:
                sublevel = superlevel + subid
                result.loc[is_healthy, (modality, side, sublevel)] = False
                result.loc[~is_healthy, (modality, side, sublevel)] = None

        return result

    def infer_superlevels(
        self,
        modalities: list[str] | None = None,
        sides: list[Literal["ipsi", "contra"]] | None = None,
        subdivisions: dict[str, list[str]] | None = None,
    ) -> pd.DataFrame:
        """Determine involvement status of an LNL's superlevel (e.g., II).

        Some LNLs have sublevels, e.g., IIa and IIb. In real data, sometimes the
        sublevels are reported, sometimes only the superlevel. This function infers the
        status of the superlevel from the sublevels.

        The superlevel's status is computed for the specified ``modalities``. If and
        what sublevels a superlevel has, is specified in ``subdivisions``.

        The resulting DataFrame will only contain the newly inferred superlevel columns.
        This way, it is straightforward to :py:meth:`~pandas.DataFrame.update` the
        original DataFrame.

        >>> df = pd.DataFrame({
        ...     ('MRI', 'ipsi'  , 'Ia' ): [True , False, False, None],
        ...     ('MRI', 'ipsi'  , 'Ib' ): [False, True , False, None],
        ...     ('MRI', 'contra', 'IIa'): [False, False, None , None],
        ...     ('MRI', 'contra', 'IIb'): [False, True , True , None],
        ...     ('CT' , 'ipsi'  , 'I'  ): [True , False, False, None],
        ... })
        >>> df.ly.infer_superlevels(modalities=["MRI"]) # doctest: +NORMALIZE_WHITESPACE
             MRI
            ipsi contra
               I     II
        0   True  False
        1   True   True
        2  False   True
        3   None   None
        """
        modalities = modalities or list(get_default_modalities().keys())
        sides = sides or ["ipsi", "contra"]
        subdivisions = subdivisions or {
            "I": ["a", "b"],
            "II": ["a", "b"],
            "V": ["a", "b"],
        }

        result = self._obj.copy().drop(self._obj.columns, axis=1)

        loop_combinations = product(modalities, sides, subdivisions.items())
        for modality, side, (superlevel, subids) in loop_combinations:
            sublevels = [superlevel + subid for subid in subids]
            sublevel_cols = [(modality, side, sublevel) for sublevel in sublevels]

            try:
                are_all_healthy = ~self._obj[sublevel_cols].any(axis=1)
                is_any_involved = self._obj[sublevel_cols].any(axis=1)
                is_unknown = self._obj[sublevel_cols].isna().all(axis=1)
            except KeyError:
                continue

            result.loc[are_all_healthy, (modality, side, superlevel)] = False
            result.loc[is_any_involved, (modality, side, superlevel)] = True
            result.loc[is_unknown, (modality, side, superlevel)] = None

        return result


def _main() -> None:
    """Run main function."""
    ...


def _run_doctests() -> None:
    """Run the module doctests."""
    import doctest

    doctest.testmod()


if __name__ == "__main__":
    _run_doctests()
