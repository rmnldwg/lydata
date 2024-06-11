"""Module for loading the lydata datasets."""
import fnmatch
import os
from collections.abc import Generator
from dataclasses import dataclass, field
from io import TextIOWrapper
from pathlib import Path
from typing import Literal

import mistletoe
import pandas as pd
from github import Auth, Github
from mistletoe.block_token import Heading
from mistletoe.markdown_renderer import MarkdownRenderer

from lydata import _repo


@dataclass
class DatasetSpec:
    """Specification of a dataset."""

    year: int | str
    institution: str
    subsite: str
    path: Path | None = None
    description: str = field(default="", repr=False)
    repo: str = field(default=_repo, repr=False)
    revision: str = field(default="main", repr=False)

    @property
    def name(self) -> str:
        """Get the name of the dataset.

        >>> spec = DatasetSpec(2023, "clb", "multisite", Path("path"), "description")
        >>> spec.name
        '2023-clb-multisite'
        """
        return f"{self.year}-{self.institution}-{self.subsite}"

    @property
    def url(self) -> str:
        """Get the URL to the dataset.

        >>> spec = DatasetSpec(2023, "clb", "multisite", Path("path"), "description")
        >>> spec.url
        'https://raw.githubusercontent.com/rmnldwg/lydata/main/2023-clb-multisite/data.csv'
        """
        return (
            "https://raw.githubusercontent.com/"
            f"{self.repo}/{self.revision}/"
            f"{self.year}-{self.institution}-{self.subsite}/data.csv"
        )

    def _load_or_fetch(self, loc: Path | str, **load_kwargs) -> pd.DataFrame:
        kwargs = {"header": [0, 1, 2]}
        kwargs.update(load_kwargs)
        return pd.read_csv(loc, **kwargs)

    def load(self, **load_kwargs) -> pd.DataFrame:
        """Load the dataset."""
        if self.path is None:
            raise ValueError("Cannot load dataset: Path not known.")

        return self._load_or_fetch(self.path, **load_kwargs)

    def fetch(self, **load_kwargs) -> pd.DataFrame:
        """Fetch the dataset from the web."""
        return self._load_or_fetch(self.url, **load_kwargs)


def remove_subheadings(elements: list, min_level: int = 1) -> list:
    """Remove anything under ``min_level`` headings."""
    filtered_elements = []

    for element in elements:
        if isinstance(element, Heading) and element.level > min_level:
            break
        filtered_elements.append(element)

    return filtered_elements


def get_description(
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
) -> Generator[DatasetSpec, None, None]:
    year = str(year)
    search_path = Path(__file__).parent.parent

    for match in search_path.glob(f"{year}-{institution}-{subsite}"):
        if match.is_dir() and (match / "data.csv").exists():
            year, institution, subsite = match.name.split("-")

            readme_path = match / "README.md"
            with open(readme_path) as readme_file:
                description = get_description(readme_file, short=True)

            yield DatasetSpec(
                year=year,
                institution=institution,
                subsite=subsite,
                path=match / "data.csv",
                description=description,
            )


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
) -> Generator[DatasetSpec, None, None]:
    github = Github(auth=_get_github_auth())

    repo = github.get_repo(repo)
    contents = repo.get_contents("")

    matches = []
    for content in contents:
        if (
            content.type == "dir"
            and fnmatch.fnmatch(content.name, f"{year}-{institution}-{subsite}")
        ):
            matches.append(content)

    for match in matches:
        year, institution, subsite = match.name.split("-")
        readme = repo.get_contents(f"{match.path}/README.md").decoded_content.decode()
        yield DatasetSpec(
            year=year,
            institution=institution,
            subsite=subsite,
            description=get_description(readme, short=True),
            repo=_repo,
        )


def available_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    where: Literal["disk", "github"] = "disk",
) -> Generator[DatasetSpec, None, None]:
    """Generate names of available datasets.

    >>> [ds.name for ds in available_datasets(where='disk')]   # doctest: +NORMALIZE_WHITESPACE
    ['2021-usz-oropharynx',
     '2021-clb-oropharynx',
     '2023-clb-multisite',
     '2023-isb-multisite']
    >>> [ds.name for ds in available_datasets(where='github')]   # doctest: +NORMALIZE_WHITESPACE
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
    for dataset_spec in available_datasets(year, institution, subsite):
        yield dataset_spec.load(**load_kwargs)


def load_dataset(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    **load_kwargs,
) -> pd.DataFrame:
    """Load the first matching dataset from the disk."""
    return next(load_datasets(year, institution, subsite, **load_kwargs))


def fetch_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    **load_kwargs,
) -> Generator[pd.DataFrame, None, None]:
    """Fetch matching datasets from the web."""
    for dataset_spec in available_datasets(year, institution, subsite):
        yield dataset_spec.fetch(**load_kwargs)


def fetch_dataset(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    **load_kwargs,
) -> pd.DataFrame:
    """Fetch the first matching dataset from the web."""
    return next(fetch_datasets(year, institution, subsite, **load_kwargs))
