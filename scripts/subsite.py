"""
Plot the distribution over primary tumor subsites.
"""
import argparse
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from lyscripts.plot.utils import COLORS
from lyscripts.utils import flatten
from tueplots import figsizes, fontsizes


def invert(mapping: dict) -> dict:
    """Invert a dictionary with lists as values."""
    result = {}
    for key, value_list in mapping.items():
        for value in value_list:
            result[value] = key

    return result


MPLSTYLE = Path(__file__).parent / ".mplstyle"
OUTPUT_NAME = Path(__file__).with_suffix(".png").name
SUBSITE_DICT = {
    "oropharynx": {
        "base of tongue":  ["C01"  , "C01.9"],
        "tonsil":          ["C09"  , "C09.0", "C09.1", "C09.8", "C09.9"],
        "other":           ["C10"  , "C10.0", "C10.1", "C10.2", "C10.3",
                            "C10.4", "C10.8", "C10.9"],
    },
    "hypopharynx": {
        "all":             ["C12"  , "C12.9",
                            "C13"  , "C13.0", "C13.1", "C13.2", "C13.8", "C13.9"],
    },
    "larynx": {
        "glottis":         ["C32.0", "C32.1", "C32.2"],
        "other":           ["C32"  , "C32.8", "C32.9"],
    },
    "oral cavity": {
        "lips":            ["C00", "C00.1", "C00.2", "C00.3", "C00.4", "C00.5",
                            "C00.8", "C00.9"],
        "tongue":          ["C02"  , "C02.0", "C02.1", "C02.2", "C02.3", "C02.4",
                            "C02.8", "C02.9",],
        "gums & cheek":    ["C03"  , "C03.0", "C03.1", "C03.9",
                            "C06"  , "C06.0", "C06.1", "C06.2", "C06.8", "C06.9",],
        "floor of mouth":  ["C04"  , "C04.0", "C04.1", "C04.8", "C04.9",],
        "palate":          ["C05"  , "C05.0", "C05.1", "C05.2", "C05.8", "C05.9",],
        "salivary glands": ["C08"  , "C08.0", "C08.1", "C08.9",],
    },
}
FLAT_SUBSITE_DICT = flatten(SUBSITE_DICT)
INVERTED_FLAT_SUBSITE_DICT = invert(FLAT_SUBSITE_DICT)
JOINED_SUBSITE_DICT = {}
for location, subdict in SUBSITE_DICT.items():
    JOINED_SUBSITE_DICT[location] = set()
    for subsite, icds in subdict.items():
        JOINED_SUBSITE_DICT[location] = JOINED_SUBSITE_DICT[location].union(
            {icd.split(".")[0] for icd in icds}
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="subsite",
        description=__doc__,
    )
    parser.add_argument(
        "--data", type=Path, default="2023-isb-multisite/data.csv",
        help="Path to the data file.",
    )
    args = parser.parse_args()

    data = pd.read_csv(args.data, header=[0, 1, 2])
    output_dir = args.data.parent / "figures"
    output_dir.mkdir(exist_ok=True)

    subsites = data[("tumor", "1", "subsite")]
    subsites = subsites.value_counts()

    grouped_subsites = defaultdict(lambda: defaultdict(int))
    for icd, count in subsites.items():
        location, subsite = INVERTED_FLAT_SUBSITE_DICT[icd]
        grouped_subsites[location][subsite] += count

    sorted_subsites = {}
    for location, subdict in grouped_subsites.items():
        sorted_subdict = dict(sorted(subdict.items(), key=lambda item: -item[1]))
        sorted_subsites[location] = sorted_subdict

    plt.style.use(MPLSTYLE)
    plt.rcParams.update(figsizes.icml2022_full(
        nrows=1, ncols=1, height_to_width_ratio=0.4,
    ))
    plt.rcParams.update(fontsizes.icml2022())
    fig, ax = plt.subplots()

    inter_loc_space, intra_loc_space = 1, 1
    cursor = 0
    positions = []
    labels = []
    max_count = 0
    for i, (location, subdict) in enumerate(sorted_subsites.items()):
        location_positions = []
        location_values = []
        for j, (subsite, count) in enumerate(subdict.items()):
            if count > max_count:
                max_count = count
            icds = {icd for icd in SUBSITE_DICT[location][subsite]}
            location_positions.append(cursor)
            location_values.append(count)
            labels.append(subsite)
            ax.text(
                x=4,
                y=cursor,
                s=", ".join(sorted(icds)),
                fontsize="small",
                verticalalignment="center",
                color=COLORS["gray"],
            )
            cursor -= intra_loc_space
        ax.barh(location_positions, location_values, label=location)

        positions = [*positions, *location_positions]
        cursor -= inter_loc_space

    ax.set_xlim(0, max_count + 10)
    ax.set_xlabel("Number of Patients")
    ax.set_yticks(positions)
    ax.set_yticklabels(labels)
    ax.legend(fontsize="medium")
    ax.grid(axis="y")

    plt.savefig(output_dir / OUTPUT_NAME, dpi=300)
