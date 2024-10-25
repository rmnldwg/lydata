"""Plot the difference of involvement patterns in two datasets as an UpSet plot."""

import lydata
import matplotlib.pyplot as plt
import upsetplot

COMMIT = "5b85184ecece020f509ab0c9f05aa5c81257ffd3"
LNLS = ["I", "II", "III", "IV", "V"]


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

    usz_indicators = upsetplot.from_indicators(usz_combined["ipsi"][LNLS]).sort_index()
    usz_index = usz_indicators.index
    hvh_indicators = upsetplot.from_indicators(hvh_combined["ipsi"][LNLS])

    for entry in usz_index:
        if entry not in hvh_indicators:
            hvh_indicators[entry] = 0

    hvh_indicators = hvh_indicators.loc[usz_index]

    upset_kwargs = {
        "subset_size": "sum",
        "sort_categories_by": "-input",
        "min_subset_size": 0,
    }

    usz_upset = upsetplot.UpSet(usz_indicators, facecolor="blue", **upset_kwargs)
    usz_ax_dict = usz_upset.plot()
    hvh_upset = upsetplot.UpSet(hvh_indicators, facecolor="red", **upset_kwargs)
    hvh_upset.plot_intersections(ax=usz_ax_dict["intersections"])
    plt.savefig("upset_diff.png", dpi=300)


if __name__ == "__main__":
    main()
