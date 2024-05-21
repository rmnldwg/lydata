"""Module containing a custom accessor and helpers for querying lydata."""
from __future__ import annotations
from typing import Any, Literal

import pandas as pd
import pandas.api.extensions as pd_ext


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


class Q:
    """Query object for filtering a DataFrame."""

    _OPERATOR_MAP = {
        "==": lambda x, y: x == y,
        "<":  lambda x, y: x <  y,
        "<=": lambda x, y: x <= y,
        ">":  lambda x, y: x >  y,
        ">=": lambda x, y: x >= y,
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
        return f"Q({self.colname!r}, {self.operator!r}, {self.value!r})"

    def __and__(self, other: Q) -> QAnd:
        return QAnd(self, other)

    def __or__(self, other: Q) -> QOr:
        return QOr(self, other)

    def __invert__(self) -> QNot:
        return QNot(self)

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


class QAnd(Q):
    """Query object for combining two queries with a logical AND."""
    def __init__(self, q1: Q, q2: Q):
        self.q1 = q1
        self.q2 = q2

    def __repr__(self):
        return f"{self.q1!r} & {self.q2!r}"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask where both queries are satisfied."""
        return self.q1.execute(df) & self.q2.execute(df)


class QOr(Q):
    """Query object for combining two queries with a logical OR."""
    def __init__(self, q1: Q, q2: Q):
        self.q1 = q1
        self.q2 = q2

    def __repr__(self):
        return f"{self.q1!r} | {self.q2!r}"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask where either query is satisfied."""
        return self.q1.execute(df) | self.q2.execute(df)


class QNot(Q):
    """Query object for negating a query."""
    def __init__(self, q: Q):
        self.q = q

    def __repr__(self):
        return f"~{self.q!r}"

    def execute(self, df: pd.DataFrame) -> pd.Series:
        """Return a boolean mask where the query is not satisfied."""
        return ~self.q.execute(df)


@pd_ext.register_dataframe_accessor("lydata")
class LydataAccessor:
    """Custom accessor for handling lymphatic involvement data."""
    def __init__(self, obj: pd.DataFrame) -> None:
        self._obj = obj

    def query(self, query: Q = None) -> pd.DataFrame:
        """Return a DataFrame with rows that satisfy the query."""
        if query is None:
            query = get_all_true

        mask = query.execute(self._obj)
        return self._obj[mask]

    def portion(self, query: Q = None, given: Q = None) -> float:
        """Return portion of rows that satisfy ``query`` given the ``given`` query."""
        if query is None:
            query = get_all_true
        if given is None:
            given = get_all_true

        given_mask = given.execute(self._obj)
        query_mask = query.execute(self._obj)

        if not given_mask.any():
            return 0

        return query_mask[given_mask].mean()


def main():
    import numpy as np

    # Example DataFrame
    data = {
        'col1': [1,      2,     5,    4,     5     ],
        'col2': [True,   False, True, True, False ],
        'col3': [np.nan, 'a',   'b',  'a',   np.nan]
    }
    df = pd.DataFrame(data)

    # Example query
    query = Q("col1", ">=", 3) & ~Q("col2", "==", False)
    given = ~Q("col3", "==", pd.isna)
    portion = df.lydata.portion(query=query, given=given)
    print(portion)  # Output the calculated portion
    print(given)
    print(query)


if __name__ == "__main__":
    main()
