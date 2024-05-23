"""Module for loading the lydata datasets."""
from pathlib import Path
from typing import Generator
from dataclasses import dataclass

import mistletoe
from mistletoe.block_token import Heading
from mistletoe.markdown_renderer import MarkdownRenderer
import pandas as pd


@dataclass
class DatasetSpec:
    year: int | str
    institution: str
    subsite: str
    path: Path
    description: str

    def load(self, **load_kwargs) -> pd.DataFrame:
        """Load the dataset."""
        kwargs = {"header": [0, 1, 2]}
        kwargs.update(load_kwargs)
        return pd.read_csv(self.path / "data.csv", **kwargs)


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

    >>> list(available_datasets())   # doctest: +NORMALIZE_WHITESPACE
    ['2023-isb-multisite',
     '2021-clb-oropharynx',
     '2021-usz-oropharynx',
     '2023-clb-multisite']
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
