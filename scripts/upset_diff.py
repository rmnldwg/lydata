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

    indicators = upsetplot.from_indicators(usz_combined["ipsi"][LNLS])
    upset = upsetplot.plot(
        indicators,
        subset_size="count",
        sort_categories_by="-input",
        min_subset_size=0,
    )
    plt.savefig("upset_diff.png", dpi=300)


if __name__ == "__main__":
    main()
