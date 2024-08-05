"""
Create a horizontal stacked bar plot showcasing the involvement prevalence for
different scenarios.
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lyscripts.plot.utils import COLORS
from subsite import INVERTED_FLAT_SUBSITE_DICT, SUBSITE_DICT
from tueplots import figsizes, fontsizes


def get_idx(df: pd.DataFrame, location: str) -> pd.Series:
    """Get the index for a given ``location`` of the primary tumor."""
    return df["tumor", "1", "subsite"].apply(
        lambda subsite: INVERTED_FLAT_SUBSITE_DICT[subsite][0]
    ) == location


OUTPUT_PATH = Path(__file__).parent.parent / Path(__file__).with_suffix(".png").name
NROWS, NCOLS = 2, 1
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
    fig, ax = plt.subplots(
        nrows=NROWS, ncols=NCOLS, sharex=True,
        gridspec_kw={"height_ratios": [3, 5]},
    )

    data = pd.read_csv(args.data, header=[0, 1, 2])
    ipsi_involvement = data["max_llh", "ipsi"]
    icd_codes = data["tumor", "1", "subsite"]

    has_II_involved = ipsi_involvement["II"] == True
    has_III_involved = ipsi_involvement["III"] == True
    is_t_stage = lambda t: data["tumor", "1", "t_stage"] == t
    is_location = lambda loc: get_idx(data, loc)
    is_gums_and_cheek = icd_codes.isin(SUBSITE_DICT["oral cavity"]["gums & cheek"])
    is_tongue = icd_codes.isin(SUBSITE_DICT["oral cavity"]["tongue"])

    loc = "oropharynx"
    starts = np.zeros(3, dtype=int)
    nums = np.zeros(3, dtype=int)
    totals = np.array([
        (is_location(loc) & ~is_t_stage(0)).sum(),
        (is_location(loc) & ~is_t_stage(0) & has_II_involved).sum(),
        (is_location(loc) & ~is_t_stage(0) & ~has_II_involved).sum(),
    ])
    for t in [1, 2, 3, 4]:
        starts += nums
        nums = np.array([
            (is_location(loc) & is_t_stage(t) & has_III_involved).sum(),
            (is_location(loc) & is_t_stage(t) & has_II_involved & has_III_involved).sum(),
            (is_location(loc) & is_t_stage(t) & ~has_II_involved & has_III_involved).sum(),
        ])
        ax[0].barh(
            y=[2, 1, 0],
            width=100 * nums / totals,
            left=100 * starts / totals,
            color=COLORS[t - 1],
            label=f"T{t}",
        )
        ax[0].set_title(loc, fontweight="bold")
        ax[0].set_yticks(
            ticks=[0, 1, 2],
            labels= [ "LNL II healthy", "LNL II involved", "overall"],
        )

    ends = starts + nums
    for j, end in enumerate(ends):
        ax[0].text(
            x=100 * (ends / totals)[j] + 1,
            y=2 - j - 0.13,
            s=f"{str(end)} / {str(totals[j])}",
        )

    loc = "oral cavity"
    starts = np.zeros(5, dtype=int)
    nums = np.zeros(5, dtype=int)
    totals = np.array([
        (is_location(loc) & ~is_t_stage(0)).sum(),
        (is_location(loc) & ~is_t_stage(0) & has_II_involved).sum(),
        (is_location(loc) & ~is_t_stage(0) & ~has_II_involved).sum(),
        (is_location(loc) & ~is_t_stage(0) & is_gums_and_cheek).sum(),
        (is_location(loc) & ~is_t_stage(0) & is_tongue).sum(),
    ])
    for t in [1, 2, 3, 4]:
        starts += nums
        nums = np.array([
            (is_location(loc) & is_t_stage(t) & has_III_involved).sum(),
            (is_location(loc) & is_t_stage(t) & has_II_involved & has_III_involved).sum(),
            (is_location(loc) & is_t_stage(t) & ~has_II_involved & has_III_involved).sum(),
            (is_location(loc) & is_t_stage(t) & is_gums_and_cheek & has_III_involved).sum(),
            (is_location(loc) & is_t_stage(t) & is_tongue & has_III_involved).sum(),
        ])
        ax[1].barh(
            y=[4, 3, 2, 1, 0],
            width=100 * nums / totals,
            left=100 * starts / totals,
            color=COLORS[t - 1],
            label=f"T{t}",
        )
        ax[1].set_title(loc, fontweight="bold")
        ax[1].set_yticks(
            ticks=[0, 1, 2, 3, 4],
            labels=["tongue tumor", "tumor in gums/cheek", "LNL II healthy", "LNL II involved", "overall"],
        )

    ends = starts + nums
    for j, end in enumerate(ends):
        ax[1].text(
            x=100 * (ends / totals)[j] + 1,
            y=4 - j - 0.13,
            s=f"{str(end)} / {str(totals[j])}",
        )

    ax[1].legend(fontsize="medium")
    ax[1].set_xlabel("Patients with involvement in LNL III [%]")
    ax[1].set_xlim(0, 40)

    plt.savefig(OUTPUT_PATH, dpi=300)
