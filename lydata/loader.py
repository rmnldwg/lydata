"""Module for loading the lydata datasets."""
from pathlib import Path
from typing import Generator
from dataclasses import dataclass, field

import mistletoe
from mistletoe.block_token import Heading
from mistletoe.markdown_renderer import MarkdownRenderer
import pandas as pd

from lydata import _repo


@dataclass
class DatasetSpec:
    year: int | str
    institution: str
    subsite: str
    path: Path
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

    def load(self, **load_kwargs) -> pd.DataFrame:
        """Load the dataset."""
        kwargs = {"header": [0, 1, 2]}
        kwargs.update(load_kwargs)
        return pd.read_csv(self.path / "data.csv", **kwargs)

    def fetch(self, **load_kwargs) -> pd.DataFrame:
        """Fetch the dataset from the web."""
        return pd.read_csv(self.url, **load_kwargs)


def remove_subheadings(elements: list, min_level: int = 1) -> list:
    """Remove anything under ``min_level`` headings."""
    filtered_elements = []

    for element in elements:
        if isinstance(element, Heading) and element.level > min_level:
            break
        filtered_elements.append(element)

    return filtered_elements


def get_description(
    path: str | Path,
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
        with open(path, mode="r", encoding="utf-8") as file:
            doc = mistletoe.Document(file)

        if short:
            doc.children = remove_subheadings(doc.children, min_level=1)

        return renderer.render(doc)


def available_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
) -> Generator[DatasetSpec, None, None]:
    """Generate names of available datasets.

    >>> [ds.name for ds in available_datasets()]   # doctest: +NORMALIZE_WHITESPACE
    ['2021-usz-oropharynx',
     '2021-clb-oropharynx',
     '2023-clb-multisite',
     '2023-isb-multisite']
    """
    year = str(year)
    search_path = Path(__file__).parent.parent

    for match in search_path.glob(f"{year}-{institution}-{subsite}"):
        if match.is_dir() and (match / "data.csv").exists():
            year, institution, subsite = match.name.split("-")
            readme_path = match / "README.md"
            description = get_description(readme_path, short=True)
            yield DatasetSpec(
                year=year,
                institution=institution,
                subsite=subsite,
                path=match,
                description=description,
            )


def load_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    **load_kwargs,
) -> Generator[pd.DataFrame, None, None]:
    """Generate datasets."""
    for dataset_spec in available_datasets(year, institution, subsite):
        yield dataset_spec.load(**load_kwargs)


def fetch_datasets(
    year: int | str = "*",
    institution: str = "*",
    subsite: str = "*",
    **load_kwargs,
) -> Generator[pd.DataFrame, None, None]:
    """Fetch datasets from the web.

    TODO: `available_dataset()` list those datasets that are present on disk. An
    improvement to the `fetch_datasets()` function would be to get the list of available
    datasets from the web.
    """
    for dataset_spec in available_datasets(year, institution, subsite):
        yield dataset_spec.fetch(**load_kwargs)
