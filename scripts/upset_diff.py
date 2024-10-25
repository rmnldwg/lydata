"""Plot the difference of involvement patterns in two datasets as an UpSet plot."""

import lydata
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import upsetplot
from lyscripts.plot.utils import COLORS

COMMIT = "5b85184ecece020f509ab0c9f05aa5c81257ffd3"
LNLS = ["I", "II", "III", "IV", "V"]


def remove_artists(ax):
    """Remove all artists from the axes."""
    for artist in (ax.lines + ax.patches + ax.collections):
        artist.remove()


def main() -> None:
    """Plot the figure."""
    usz_combined = next(lydata.load_datasets(
        year=2021,
        institution="usz",
        subsite="oropharynx",
        skip_disk=True,
        ref=COMMIT,
    )).ly.combine()
    hvh_combined = next(lydata.load_datasets(
        year=2024,
        institution="hvh",
        subsite="oropharynx",
        skip_disk=True,
        ref=COMMIT,
    )).ly.combine()

    usz_prevalences = (
        100 * usz_combined["ipsi"][LNLS].sum(axis="index") / len(usz_combined)
    )
    hvh_prevalences = (
        100 * hvh_combined["ipsi"][LNLS].sum(axis="index") / len(hvh_combined)
    )
    usz_countable_indicators = upsetplot.from_indicators(usz_combined["ipsi"][LNLS])
    hvh_countable_indicators = upsetplot.from_indicators(hvh_combined["ipsi"][LNLS])

    joined_index = usz_countable_indicators.index.unique().union(
        hvh_countable_indicators.index.unique()
    ).sort_values()

    usz_summable_indicators = pd.Series(index=joined_index, dtype=float)
    hvh_summable_indicators = pd.Series(index=joined_index, dtype=float)
    usz_total = len(usz_combined)
    hvh_total = len(hvh_combined)

    for index in joined_index:
        usz_summable_indicators.loc[index] = (
            100 * len(usz_countable_indicators.get(index, [])) / usz_total
        )
        hvh_summable_indicators.loc[index] = (
            100 * len(hvh_countable_indicators.get(index, [])) / hvh_total
        )

    width = 0.4

    hvh_upset = upsetplot.UpSet(
        hvh_summable_indicators,
        subset_size="sum",
        sort_categories_by="-input",
        min_subset_size=0,
        totals_plot_elements=4,
        facecolor=COLORS["blue"],
    )
    ax_dict = hvh_upset.plot()
    hvh_upset.style_subsets(absent=["I", "II", "III", "IV", "V"])

    remove_artists(ax_dict["intersections"])
    remove_artists(ax_dict["totals"])

    ax_dict["intersections"].bar(
        x=np.arange(len(hvh_summable_indicators)) + 0.1,
        height=hvh_summable_indicators,
        width=width,
        color=COLORS["red"],
    )
    ax_dict["intersections"].bar(
        x=np.arange(len(usz_summable_indicators)) - 0.1,
        height=usz_summable_indicators,
        width=width,
        color=COLORS["green"],
    )
    ax_dict["intersections"].set_ylabel("Frequency\n of specific patterns (%)")

    ax_dict["totals"].barh(
        y=np.arange(len(usz_prevalences)) + 0.1,
        width=usz_prevalences[::-1],
        height=width,
        color=COLORS["red"],
    )
    ax_dict["totals"].barh(
        y=np.arange(len(hvh_prevalences)) - 0.1,
        width=hvh_prevalences[::-1],
        height=width,
        color=COLORS["green"],
    )
    ax_dict["totals"].set_xlabel("Prevalence\nof LNL involvement (%)")

    plt.savefig("upset_diff.png", dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
