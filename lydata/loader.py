"""Module for loading the lydata datasets."""

import fnmatch
import logging
import os
from collections.abc import Generator, Iterable
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path
from typing import Literal

import mistletoe
import pandas as pd
from github import Auth, Github
from mistletoe.block_token import Heading
from mistletoe.markdown_renderer import MarkdownRenderer
from mistletoe.token import Token
from pydantic import BaseModel, Field, constr

from lydata import _repo

logger = logging.getLogger(__name__)

low_min1_str = constr(to_lower=True, min_length=1)


class LyDatasetConfig(BaseModel):
    """Specification of a dataset."""

    year: int = Field(
        gt=0,
        lt=datetime.now().year,
        description="Release year of dataset.",
    )
    institution: low_min1_str = Field(
        description="Institution's short code. E.g., University Hospital Zurich: `usz`."
    )
    subsite: low_min1_str = Field(description="Subsite(s) this dataset covers.")
    repo: low_min1_str = Field(default=_repo, description="GitHub `repository/owner`.")
    revision: low_min1_str = Field(
        default="main",
        description="Branch/tag/commit of the repo.",
    )

    @property
    def name(self) -> str:
        """Get the name of the dataset.

        >>> conf = LyDatasetConfig(year=2023, institution="clb", subsite="multisite")
        >>> conf.name
        '2023-clb-multisite'
        """
        return f"{self.year}-{self.institution}-{self.subsite}"

    @property
    def path(self) -> Path:
        """Get the path to the dataset.

        >>> conf = LyDatasetConfig(year="2021", institution="usz", subsite="oropharynx")
        >>> conf.path.exists()
        True
        """
        install_loc = Path(__file__).parent.parent
        return install_loc / self.name / "data.csv"

    @property
    def url(self) -> str:
        """Get the URL to the dataset.

        >>> conf = LyDatasetConfig(year=2023, institution="isb", subsite="multisite")
        >>> conf.url
        'https://raw.githubusercontent.com/rmnldwg/lydata/main/2023-isb-multisite/data.csv'
        """
        return (
            "https://raw.githubusercontent.com/"
            f"{self.repo}/{self.revision}/"
            f"{self.year}-{self.institution}-{self.subsite}/data.csv"
        )

    def get_description(self) -> str:
        """Get the description of the dataset.

        First, try to load it from the `README.md` file that should sit right next to
        the `data.csv` file. If that fails, try to look for the `README.md` file in the
        GitHub repository.

        >>> conf = LyDatasetConfig(year=2021, institution="clb", subsite="oropharynx")
        >>> print(conf.get_description())   # doctest: +ELLIPSIS
        # 2021 CLB Oropharynx
        ...
        """
        readme_path = self.path.with_name("README.md")
        if readme_path.exists():
            with open(readme_path, encoding="utf-8") as readme:
                return format_description(readme, short=True)

        logger.info(f"Readme not found at {readme_path}. Searching on GitHub...")
        gh = Github(auth=_get_github_auth())
        repo = gh.get_repo(self.repo)
        readme = repo.get_contents(f"{self.name}/README.md").decoded_content.decode()
        return format_description(readme, short=True)

    def _load_or_fetch(self, loc: Path | str, **load_kwargs) -> pd.DataFrame:
        kwargs = {"header": [0, 1, 2]}
        kwargs.update(load_kwargs)
        df = pd.read_csv(loc, **kwargs)
        df.attrs.update(self.model_dump())
        return df

    def load(self, **load_kwargs) -> pd.DataFrame:
        """Load the dataset."""
        if self.path is None:
            raise ValueError("Cannot load dataset: Path not known.")

        return self._load_or_fetch(self.path, **load_kwargs)

    def fetch(self, **load_kwargs) -> pd.DataFrame:
        """Fetch the dataset from the web."""
        return self._load_or_fetch(self.url, **load_kwargs)


def remove_subheadings(tokens: Iterable[Token], min_level: int = 1) -> list[Token]:
    """Remove anything under ``min_level`` headings.

    With this, one can truncate markdown content to e.g. to the top-level heading and
    the text that follows immediately after. Any subheadings after that will be removed.
    """
    for i, token in enumerate(tokens):
        if isinstance(token, Heading) and token.level > min_level:
            return tokens[:i]

    return list(tokens)


def format_description(
    readme: TextIOWrapper | str,
    short: bool = False,
    max_line_length: int = 60,
) -> str:
    """Get a markdown description from a file.

    Truncate the description before the first second-level heading if ``short``
    is set to ``True``.
    """
    with MarkdownRenderer(
        max_line_length=max_line_length,
        normalize_whitespace=True,
    ) as renderer:
        doc = mistletoe.Document(readme)

        if short:
            doc.children = remove_subheadings(doc.children, min_level=1)

        return renderer.render(doc)


def _available_datasets_on_disk(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
) -> Generator[LyDatasetConfig, None, None]:
    year = str(year)
    search_path = Path(__file__).parent.parent

    for match in search_path.glob(f"{year}-{institution}-{subsite}"):
        if match.is_dir() and (match / "data.csv").exists():
            year, institution, subsite = match.name.split("-")
            yield LyDatasetConfig(year=year, institution=institution, subsite=subsite)


def _get_github_auth() -> Auth:
    token = os.getenv("GITHUB_TOKEN")
    user = os.getenv("GITHUB_USER")
    password = os.getenv("GITHUB_PASSWORD")

    if token:
        return Auth.Token(token)

    if user and password:
        return Auth.Login(user, password)

    raise ValueError("Neither GITHUB_TOKEN nor GITHUB_USER and GITHUB_PASSWORD set.")


def _available_datasets_on_github(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    repo: str = _repo,
    # revision: str = "main",   # TODO: Add revision parameter
) -> Generator[LyDatasetConfig, None, None]:
    gh = Github(auth=_get_github_auth())

    repo = gh.get_repo(repo)
    contents = repo.get_contents("")

    matches = []
    for content in contents:
        if content.type == "dir" and fnmatch.fnmatch(
            content.name, f"{year}-{institution}-{subsite}"
        ):
            matches.append(content)

    for match in matches:
        year, institution, subsite = match.name.split("-")
        yield LyDatasetConfig(year=year, institution=institution, subsite=subsite)


def available_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    where: Literal["disk", "github"] = "disk",
) -> Generator[LyDatasetConfig, None, None]:
    """Generate names of available datasets.

    >>> avail_gen = available_datasets(where='disk')
    >>> sorted([ds.name for ds in avail_gen])   # doctest: +NORMALIZE_WHITESPACE
    ['2021-clb-oropharynx',
     '2021-usz-oropharynx',
     '2023-clb-multisite',
     '2023-isb-multisite']
    >>> avail_gen = available_datasets(where='github')
    >>> sorted([ds.name for ds in avail_gen])   # doctest: +NORMALIZE_WHITESPACE
    ['2021-clb-oropharynx',
     '2021-usz-oropharynx',
     '2023-clb-multisite',
     '2023-isb-multisite']
    """
    if where == "disk":
        yield from _available_datasets_on_disk(year, institution, subsite)
    elif where == "github":
        yield from _available_datasets_on_github(year, institution, subsite)
    else:
        raise ValueError(f"Unknown source: {where}")


def load_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    **load_kwargs,
) -> Generator[pd.DataFrame, None, None]:
    """Load matching datasets from the disk."""
    for dataset_conf in available_datasets(year, institution, subsite):
        yield dataset_conf.load(**load_kwargs)


def load_dataset(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    **load_kwargs,
) -> pd.DataFrame:
    """Load the first matching dataset from the disk.

    Note that datasets loaded (or fetched) with this function will have the
    dataset config stored in the ``attrs`` attribute. See below for an
    example of how to access the dataset config.

    >>> ds = load_dataset(year="2021", institution='clb', subsite='oropharynx')
    >>> ds.attrs["year"]
    2021
    >>> conf_from_ds = LyDatasetConfig(**ds.attrs)
    >>> conf_from_ds.name
    '2021-clb-oropharynx'
    """
    return next(load_datasets(year, institution, subsite, **load_kwargs))


def fetch_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    **load_kwargs,
) -> Generator[pd.DataFrame, None, None]:
    """Fetch matching datasets from the web."""
    for dataset_conf in available_datasets(year, institution, subsite):
        yield dataset_conf.fetch(**load_kwargs)


def fetch_dataset(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    **load_kwargs,
) -> pd.DataFrame:
    """Fetch the first matching dataset from the web."""
    return next(fetch_datasets(year, institution, subsite, **load_kwargs))


def join_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    method: Literal["fetch", "load"] = "load",
    **load_or_fetch_kwargs,
) -> pd.DataFrame:
    """Join matching datasets from the disk."""
    if method == "fetch":
        gen = fetch_datasets(year, institution, subsite, **load_or_fetch_kwargs)
    elif method == "load":
        gen = load_datasets(year, institution, subsite, **load_or_fetch_kwargs)
    else:
        raise ValueError(f"Unknown method: {method}")

    return pd.concat(list(gen), axis="index", ignore_index=True)
