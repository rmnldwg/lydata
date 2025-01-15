"""Provides functions to easily load lyDATA CSV tables as :py:class:`pandas.DataFrame`.

The loading itself is implemented in the :py:class:`.LyDataset` class, which
is a :py:class:`pydantic.BaseModel` subclass. It validates the unique specification
that identifies a dataset and then allows loading it from the disk (if present) or
from GitHub.

The :py:func:`available_datasets` function can be used to create a generator of such
:py:class:`.LyDataset` instances, corresponding to all available datasets that
are either found on disk or on GitHub.

Consequently, the :py:func:`load_datasets` function can be used to load all datasets
matching the given specs/pattern. It takes the same arguments as the function
:py:func:`available_datasets` but returns a generator of :py:class:`pandas.DataFrame`
instead of :py:class:`.LyDataset`.

Lastly, with the :py:func:`join_datasets` function, one can load and concatenate all
datasets matching the given specs/pattern into a single :py:class:`pandas.DataFrame`.

The docstring of all functions contains some basic doctest examples.
"""

import fnmatch
import os
import warnings
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import numpy as np  # noqa: F401
import pandas as pd
from github import Auth, Github, Repository
from github.ContentFile import ContentFile
from loguru import logger
from pydantic import BaseModel, Field, PrivateAttr, constr

_default_repo_name = "rmnldwg/lydata"
low_min1_str = constr(to_lower=True, min_length=1)


class SkipDiskError(Exception):
    """Raised when the user wants to skip loading from disk."""


class LyDataset(BaseModel):
    """Specification of a dataset."""

    year: int = Field(
        gt=0,
        le=datetime.now().year,
        description="Release year of dataset.",
    )
    institution: low_min1_str = Field(
        description="Institution's short code. E.g., University Hospital Zurich: `usz`."
    )
    subsite: low_min1_str = Field(
        description="Tumor subsite(s) patients in this dataset were diagnosed with.",
    )
    repo_name: low_min1_str = Field(
        default=_default_repo_name,
        description="GitHub `repository/owner`.",
    )
    ref: low_min1_str = Field(
        default="main",
        description="Branch/tag/commit of the repo.",
    )
    _content_file: ContentFile | None = PrivateAttr(default=None)

    @property
    def name(self) -> str:
        """Get the name of the dataset.

        >>> conf = LyDataset(year=2023, institution="clb", subsite="multisite")
        >>> conf.name
        '2023-clb-multisite'
        """
        return f"{self.year}-{self.institution}-{self.subsite}"

    @property
    def path_on_disk(self) -> Path:
        """Get the path to the dataset.

        >>> conf = LyDataset(year="2021", institution="usz", subsite="oropharynx")
        >>> conf.path_on_disk.exists()
        True
        """
        install_loc = Path(__file__).parent.parent
        return install_loc / self.name / "data.csv"

    def get_repo(
        self,
        token: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> Repository:
        """Get the GitHub repository object.

        With the arguments ``token`` or ``user`` and ``password``, one can authenticate
        with GitHub. If no authentication is provided, the function will try to use the
        environment variables ``GITHUB_TOKEN`` or ``GITHUB_USER`` and
        ``GITHUB_PASSWORD``.

        >>> conf = LyDataset(
        ...     year=2021,
        ...     institution="clb",
        ...     subsite="oropharynx",
        ... )
        >>> conf.get_repo().full_name == conf.repo_name
        True
        >>> conf.get_repo().visibility
        'public'
        """
        auth = _get_github_auth(token=token, user=user, password=password)
        gh = Github(auth=auth)
        return gh.get_repo(self.repo_name)

    def get_content_file(
        self,
        token: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> ContentFile:
        """Get the GitHub content file of the data CSV.

        This method always tries to fetch the most recent version of the file.

        >>> conf = LyDataset(
        ...     year=2023,
        ...     institution="usz",
        ...     subsite="hypopharynx-larynx",
        ...     repo_name="rmnldwg/lydata.private",
        ...     ref="2023-usz-hypopharynx-larynx",
        ... )
        >>> conf.get_content_file()
        ContentFile(path="2023-usz-hypopharynx-larynx/data.csv")
        """
        if self._content_file is not None:
            if self._content_file.update():
                logger.info(f"Content file of {self.name} was updated.")
            return self._content_file

        repo = self.get_repo(token=token, user=user, password=password)
        self._content_file = repo.get_contents(f"{self.name}/data.csv", ref=self.ref)
        return self._content_file

    def get_dataframe(
        self,
        use_github: bool = False,
        token: str | None = None,
        user: str | None = None,
        password: str | None = None,
        **load_kwargs,
    ) -> pd.DataFrame:
        """Load the ``data.csv`` file from disk or from GitHub.

        One can also choose to ``use_github``. Any keyword arguments are passed to
        :py:func:`pandas.read_csv`.

        The method will store the output of :py:meth:`~pydantic.BaseModel.model_dump`
        in the :py:attr:`~pandas.DataFrame.attrs` attribute of the returned
        :py:class:`~pandas.DataFrame`.

        >>> conf = LyDataset(year=2021, institution="clb", subsite="oropharynx")
        >>> df_from_disk = conf.get_dataframe()
        >>> df_from_disk.shape
        (263, 82)
        >>> df_from_github = conf.get_dataframe(use_github=True)
        >>> np.all(df_from_disk.fillna(0) == df_from_github.fillna(0))
        np.True_
        """
        kwargs = {"header": [0, 1, 2]}
        kwargs.update(load_kwargs)

        if use_github:
            msg = f"Trying to load dataset {self.name} from GitHub."
            from_location = self.get_content_file(
                token=token, user=user, password=password
            ).download_url
        else:
            msg = f"Trying to load dataset {self.name} from disk."
            from_location = self.path_on_disk

        logger.info(msg)
        df = pd.read_csv(from_location, **kwargs)
        df.attrs.update(self.model_dump())
        return df


def _available_datasets_on_disk(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    search_paths: list[Path] | None = None,
) -> Generator[LyDataset, None, None]:
    pattern = f"{str(year)}-{institution}-{subsite}"
    search_paths = search_paths or [Path(__file__).parent.parent]

    for search_path in search_paths:
        for match in search_path.glob(pattern):
            if match.is_dir() and (match / "data.csv").exists():
                year, institution, subsite = match.name.split("-", maxsplit=2)
                yield LyDataset(
                    year=year,
                    institution=institution,
                    subsite=subsite,
                )


def _get_github_auth(
    token: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> Auth:
    token = token or os.getenv("GITHUB_TOKEN")
    user = user or os.getenv("GITHUB_USER")
    password = password or os.getenv("GITHUB_PASSWORD")

    if token:
        logger.debug("Using GITHUB_TOKEN for authentication.")
        return Auth.Token(token)

    if user and password:
        logger.debug("Using GITHUB_USER and GITHUB_PASSWORD for authentication.")
        return Auth.Login(user, password)

    raise ValueError("Neither GITHUB_TOKEN nor GITHUB_USER and GITHUB_PASSWORD set.")


def _available_datasets_on_github(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    repo_name: str = _default_repo_name,
    ref: str = "main",
) -> Generator[LyDataset, None, None]:
    gh = Github(auth=_get_github_auth())

    repo = gh.get_repo(repo_name)
    contents = repo.get_contents(path="", ref=ref)

    matches = []
    for content in contents:
        if content.type == "dir" and fnmatch.fnmatch(
            content.name, f"{year}-{institution}-{subsite}"
        ):
            matches.append(content)

    for match in matches:
        year, institution, subsite = match.name.split("-", maxsplit=2)
        yield LyDataset(
            year=year,
            institution=institution,
            subsite=subsite,
            repo_name=repo.full_name,
            ref=ref,
        )


def available_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    search_paths: list[Path] | None = None,
    use_github: bool = False,
    repo_name: str = _default_repo_name,
    ref: str = "main",
) -> Generator[LyDataset, None, None]:
    """Generate :py:class:`.LyDataset` instances of available datasets.

    The arguments ``year``, ``institution``, and ``subsite`` represent glob patterns
    and all datasets matching these patterns can be iterated over using the returned
    generator.

    By default, the functions will look for datasets on the disk at paths specified
    in the ``search_paths`` argument. If no paths are provided, it will look in the
    the parent directory of the directory containing this file. If the library is
    installed, this will be the ``site-packages`` directory.

    With ``use_github`` set to ``True``, the function will not look for datasets on
    disk, but will instead look for them on GitHub. The ``repo`` and ``ref`` arguments
    can be used to specify the repository and the branch/tag/commit to look in.

    >>> avail_gen = available_datasets()
    >>> sorted([ds.name for ds in avail_gen])   # doctest: +NORMALIZE_WHITESPACE
    ['2021-clb-oropharynx',
     '2021-usz-oropharynx',
     '2023-clb-multisite',
     '2023-isb-multisite']
    >>> avail_gen = available_datasets(
    ...     repo_name="rmnldwg/lydata.private",
    ...     ref="2024-umcg-hypopharynx-larynx",
    ...     use_github=True,
    ... )
    >>> sorted([ds.name for ds in avail_gen])   # doctest: +NORMALIZE_WHITESPACE
    ['2021-clb-oropharynx',
     '2021-usz-oropharynx',
     '2023-clb-multisite',
     '2023-isb-multisite',
     '2024-umcg-hypopharynx-larynx']
    >>> avail_gen = available_datasets(
    ...     institution="hvh",
    ...     ref="6ac98d",
    ...     use_github=True,
    ... )
    """
    if not use_github:
        if repo_name != _default_repo_name or ref != "main":
            warnings.warn(
                "Parameters `repo` and `ref` are ignored, unless `use_github` "
                "is set to `True`."
            )
        yield from _available_datasets_on_disk(
            year=year,
            institution=institution,
            subsite=subsite,
            search_paths=search_paths,
        )
    else:
        yield from _available_datasets_on_github(
            year=year,
            institution=institution,
            subsite=subsite,
            repo_name=repo_name,
            ref=ref,
        )


def load_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    search_paths: list[Path] | None = None,
    use_github: bool = False,
    repo_name: str = _default_repo_name,
    ref: str = "main",
    **kwargs,
) -> Generator[pd.DataFrame, None, None]:
    """Load matching datasets from the disk.

    It loads every dataset from the :py:class:`.LyDataset` instances generated by
    the :py:func:`available_datasets` function, which also receives all arguments of
    this function.
    """
    dset_confs = available_datasets(
        year=year,
        institution=institution,
        subsite=subsite,
        search_paths=search_paths,
        use_github=use_github,
        repo_name=repo_name,
        ref=ref,
    )
    for dset_conf in dset_confs:
        yield dset_conf.get_dataframe(use_github=use_github, **kwargs)


def _run_doctests() -> None:
    """Run the doctests."""
    import doctest

    doctest.testmod()


if __name__ == "__main__":
    _run_doctests()
