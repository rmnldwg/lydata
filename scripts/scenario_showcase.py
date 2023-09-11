"""
Create a horizontal stacked bar plot showcasing the involvement prevalence for
different scenarios.
"""
from pathlib import Path
import argparse

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tueplots import figsizes, fontsizes

from lyscripts.plot.utils import COLORS

from subsite import INVERTED_FLAT_SUBSITE_DICT


def get_idx(df: pd.DataFrame, location: str) -> pd.Series:
    """Get the index for a given ``location`` of the primary tumor."""
    return df["tumor", "1", "subsite"].apply(
        lambda subsite: INVERTED_FLAT_SUBSITE_DICT[subsite][0]
    ) == location


OUTPUT_PATH = Path(__file__).parent.parent / Path(__file__).with_suffix(".png").name
NROWS, NCOLS = 3, 1
COLORS = [COLORS["green"], COLORS["blue"], COLORS["orange"], COLORS["red"]]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=Path(__file__).parent.parent / "enhanced.csv",
        help="Path to the data file.",
    )
    parser.add_argument(
        "--mplstyle", type=Path, default=Path(__file__).parent / ".mplstyle",
        help="Path to the matplotlib style file.",
    )
    args = parser.parse_args()

    plt.style.use(args.mplstyle)
    plt.rcParams.update(figsizes.icml2022_full(
        nrows=NROWS, ncols=NCOLS, height_to_width_ratio=0.2,
    ))
    plt.rcParams.update(fontsizes.icml2022())
    fig, ax = plt.subplots(nrows=NROWS, ncols=NCOLS, sharex=True)

    data = pd.read_csv(args.data, header=[0, 1, 2])
    ipsi_involvement = data["max_llh", "ipsi"]

    has_II_involved = ipsi_involvement["II"] == True
    has_III_involved = ipsi_involvement["III"] == True
    is_t_stage = lambda t: data["tumor", "1", "t_stage"] == t
    is_location = lambda loc: get_idx(data, loc)

    for i, loc in enumerate(["oropharynx", "oral cavity", "hypopharynx"]):
        starts = np.zeros(3, dtype=int)
        nums = np.zeros(3, dtype=int)
        totals = np.array([
            is_location(loc).sum(),
            (is_location(loc) & has_II_involved).sum(),
            (is_location(loc) & ~has_II_involved).sum(),
        ])
        for t in [1, 2, 3, 4]:
            starts += nums
            nums = np.array([
                (is_location(loc) & is_t_stage(t) & has_III_involved).sum(),
                (is_location(loc) & is_t_stage(t) & has_II_involved & has_III_involved).sum(),
                (is_location(loc) & is_t_stage(t) & ~has_II_involved & has_III_involved).sum(),
            ])
            ax[i].barh(
                y=[2, 1, 0],
                width=100 * nums / totals,
                left=100 * starts / totals,
                color=COLORS[t - 1],
                label=f"T{t}",
            )
            ax[i].set_title(loc, fontweight="bold")
            ax[i].set_yticks(
                ticks=[0, 1, 2],
                labels= [ "LNL II healthy", "LNL II involved", "overall"],
            )

        ends = starts + nums
        for j, end in enumerate(ends):
            ax[i].text(
                x=100 * (ends / totals)[j] + 1,
                y=2 - j - 0.13,
                s=f"{str(end)} / {str(totals[j])}",
            )

        ax[1].legend(fontsize="medium")
        ax[-1].set_xlabel("Percentage of Patients")
        ax[-1].set_xlim(0, 55)

    plt.savefig(OUTPUT_PATH, dpi=300)
