"""Module containing a custom accessor and helpers for querying lydata."""
from __future__ import annotations

from dataclasses import dataclass
from operator import getitem
from typing import Any, Literal

import pandas as pd
import pandas.api.extensions as pd_ext

from lydata.validator import lydata_schema

_SHORTNAME_MAP = {
    "age": ("patient", "#", "age"),
    "hpv": ("patient", "#", "hpv_status"),
    "smoke": ("patient", "#", "nicotine_abuse"),
    "alcohol": ("patient", "#", "alcohol_abuse"),
    "t_stage": ("tumor", "1", "t_stage"),
    "n_stage": ("patient", "#", "n_stage"),
    "m_stage": ("patient", "#", "m_stage"),
    "midext": ("tumor", "1", "extension"),
}
"""Map of short names for columns."""


def get_all_true(df: pd.DataFrame) -> pd.Series:
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
    """Combinable query object for filtering a DataFrame."""

    _OPERATOR_MAP = {
        "==": lambda series, value: series == value,
        "<":  lambda series, value: series <  value,
        "<=": lambda series, value: series <= value,
        ">":  lambda series, value: series >  value,
        ">=": lambda series, value: series >= value,
        "!=": lambda series, value: series != value,    # same as ~Q(series, "==", value)
        "in": lambda series, value: series.isin(value), # value is a list
    }

    def __init__(
        self,
        column: str,
        operator: Literal["==", "<", "<=", ">", ">="],
        value: Any,
    ):
        """Create query object that can compare a ``column`` with a ``value``."""
        self.colname = column
        self.operator = operator
        self.value = value

    def __repr__(self):
        """Return a string representation of the query."""
        return f"Q({self.colname!r}, {self.operator!r}, {self.value!r})"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask where the query is satisfied for ``df``."""
        try:
            colname = _SHORTNAME_MAP[self.colname]
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

    def __init__(self, q1: QTypes, q2: QTypes):
        """Combine two queries with a logical AND."""
        self.q1 = q1
        self.q2 = q2

    def __repr__(self):
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

    def __init__(self, q1: QTypes, q2: QTypes):
        """Combine two queries with a logical OR."""
        self.q1 = q1
        self.q2 = q2

    def __repr__(self):
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

    def __init__(self, q: QTypes):
        """Negate the given query ``q``."""
        self.q = q

    def __repr__(self):
        """Return a string representation of the query."""
        return f"~{self.q!r}"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask where the query is not satisfied."""
        return ~self.q.execute(df)


class NoneQ(CombineQMixin):
    """Query object that always returns the entire DataFrame. Useful as default."""

    def __repr__(self):
        """Return a string representation of the query."""
        return "NoneQ()"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask with all entries set to ``True``."""
        return get_all_true(df)


QTypes = Q | AndQ | OrQ | NotQ


@dataclass
class QueryPortion:
    """Dataclass for storing the portion of a query."""

    match: int
    total: int

    def __post_init__(self):
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


@pd_ext.register_dataframe_accessor("lydata")
class LydataAccessor:
    """Custom accessor for handling lymphatic involvement data."""

    def __init__(self, obj: pd.DataFrame) -> None:
        """Initialize the accessor with a DataFrame."""
        self._obj = obj

    def __getattr__(self, name: str) -> Any:
        """Access columns by short name.

        >>> df = pd.DataFrame({("patient", "#", "age"): [61, 52, 73]})
        >>> df.lydata.age
        0    61
        1    52
        2    73
        Name: (patient, #, age), dtype: int64
        >>> df.lydata.foo
        Traceback (most recent call last):
            ...
        AttributeError: Attribute 'foo' not found.
        """
        try:
            return getitem(self._obj, _SHORTNAME_MAP[name])
        except KeyError as key_err:
            raise AttributeError(f"Attribute {name!r} not found.") from key_err

    def validate(self) -> None:
        """Validate the DataFrame against the lydata schema."""
        lydata_schema.validate(self._obj)

    def query(self, query: QTypes = None) -> pd.DataFrame:
        """Return a DataFrame with rows that satisfy the ``query``."""
        mask = (query or NoneQ()).execute(self._obj)
        return self._obj[mask]

    def portion(self, query: QTypes = None, given: QTypes = None) -> QueryPortion:
        """Compute how many rows satisfy a ``query``, ``given`` some other conditions.

        Returns a tuple with the number of matches and the number of total rows, such
        that the ratio of the two is the portion of interest.

        >>> df = pd.DataFrame({'x': [1, 2, 3]})
        >>> df.lydata.portion(query=Q('x', '==', 2), given=Q('x', '>', 1))
        QueryPortion(match=1, total=2)
        >>> df.lydata.portion(query=Q('x', '==', 2), given=Q('x', '>', 3))
        QueryPortion(match=0, total=0)
        """
        given_mask = (given or NoneQ()).execute(self._obj)
        query_mask = (query or NoneQ()).execute(self._obj)

        return QueryPortion(
            match=query_mask[given_mask].sum(),
            total=given_mask.sum(),
        )


def main():
    """Run the module's doctests."""
    pass


if __name__ == "__main__":
    main()
