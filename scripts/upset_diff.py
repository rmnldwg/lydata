"""Plot the difference of involvement patterns in two datasets as an UpSet plot."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import upsetplot
from lyscripts.plots import COLORS
from shared import LNLS, MPLSTYLE, remove_artists
from tueplots import figsizes, fontsizes

import lydata

OUTPUT_NAME = Path(__file__).with_suffix(".png").name


def get_parser() -> argparse.ArgumentParser:
    """Return the argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commit",
        type=str,
        help="The commit hash at which to compare the datasets.",
        default="5b85184ecece020f509ab0c9f05aa5c81257ffd3",
    )
    parser.add_argument(
        "--first-dataset",
        type=str,
        default="2021-usz-oropharynx",
    )
    parser.add_argument(
        "--second-dataset",
        type=str,
        default="2024-hvh-oropharynx",
    )
    return parser


def kwargs_from_option(option: str) -> dict:
    """Return the load_kwargs for the given option."""
    year, institution, subsite = option.split("-")
    return {
        "year": int(year),
        "institution": institution,
        "subsite": subsite,
        "use_github": True,
    }


def calculate_summable_indicators(first_combined, second_combined):
    """Calculate the summable indicators for the two datasets."""
    first_countable_inds = upsetplot.from_indicators(first_combined["ipsi"][LNLS])
    second_countable_inds = upsetplot.from_indicators(second_combined["ipsi"][LNLS])

    multiindex = pd.MultiIndex.from_product([[False, True]] * len(LNLS), names=LNLS)

    first_summable_inds = pd.Series(index=multiindex, dtype=float)
    second_summable_inds = pd.Series(index=multiindex, dtype=float)
    first_total = len(first_combined)
    second_total = len(second_combined)

    to_drop = []

    for index in multiindex:
        first_percent = 100 * len(first_countable_inds.get(index, [])) / first_total
        second_percent = 100 * len(second_countable_inds.get(index, [])) / second_total

        if first_percent == 0 and second_percent == 0:
            to_drop.append(index)

        first_summable_inds.loc[index] = first_percent
        second_summable_inds.loc[index] = second_percent

    first_summable_inds = first_summable_inds.drop(to_drop)
    second_summable_inds = second_summable_inds.drop(to_drop)

    return first_summable_inds, second_summable_inds


def main() -> None:
    """Plot the figure."""
    args = get_parser().parse_args()

    first_load_kwargs = kwargs_from_option(args.first_dataset)
    first_load_kwargs["ref"] = args.commit
    first_combined = next(lydata.load_datasets(**first_load_kwargs)).ly.combine()

    second_load_kwargs = kwargs_from_option(args.second_dataset)
    second_load_kwargs["ref"] = args.commit
    second_combined = next(lydata.load_datasets(**second_load_kwargs)).ly.combine()

    first_total = len(first_combined)
    second_total = len(second_combined)
    first_prevs = 100 * first_combined["ipsi"][LNLS].sum(axis="index") / first_total
    second_prevs = 100 * second_combined["ipsi"][LNLS].sum(axis="index") / second_total
    first_summable_inds, second_summable_inds = calculate_summable_indicators(
        first_combined,
        second_combined,
    )

    first_institution = first_load_kwargs["institution"].upper()
    second_institution = second_load_kwargs["institution"].upper()

    plt.style.use(MPLSTYLE)
    plt.rcParams.update(
        figsizes.icml2022_full(
            nrows=1,
            ncols=2,
            height_to_width_ratio=0.75,
        )
    )
    plt.rcParams.update(fontsizes.icml2022())

    width = 0.35

    second_upset = upsetplot.UpSet(
        second_summable_inds,
        subset_size="sum",
        sort_categories_by="-input",
        sort_by="input",
        min_subset_size=0,
        totals_plot_elements=6,
        facecolor="#5d749d",
    )
    ax_dict = second_upset.plot()

    remove_artists(ax_dict["intersections"])
    remove_artists(ax_dict["totals"])

    first_color = COLORS["blue"]
    second_color = COLORS["red"]

    ax_dict["intersections"].bar(
        x=np.arange(len(second_summable_inds)) - width / 2,
        height=second_summable_inds,
        width=width,
        color=first_color,
        label=f"{first_institution} ({first_total:d} patients)",
    )
    ax_dict["intersections"].bar(
        x=np.arange(len(first_summable_inds)) + width / 2,
        height=first_summable_inds,
        width=width,
        color=second_color,
        label=f"{second_institution} ({second_total:d} patients)",
    )
    ax_dict["intersections"].set_ylabel("Frequency\n of specific patterns (%)")
    ax_dict["intersections"].legend(loc="upper right")

    ax_dict["totals"].barh(
        y=np.arange(len(first_prevs)) + width / 2,
        width=first_prevs[::-1],
        height=width,
        color=first_color,
    )
    ax_dict["totals"].barh(
        y=np.arange(len(second_prevs)) - width / 2,
        width=second_prevs[::-1],
        height=width,
        color=second_color,
    )
    ax_dict["totals"].set_xlabel("Prevalence\nof LNL involvement (%)")

    output_dir = Path(args.second_dataset) / "figures"
    output_dir.mkdir(exist_ok=True, parents=True)
    plt.savefig(output_dir / OUTPUT_NAME, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
