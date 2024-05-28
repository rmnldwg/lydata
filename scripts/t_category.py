"""
Plot the distribution over patient's T-category.
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from lyscripts.plot.utils import COLORS
from tueplots import figsizes, fontsizes


def create_label(percent):
    """Create label for pie chart."""
    if percent < 5:
        return ""

    return f"{percent:.0f}%"


MPLSTYLE = Path(__file__).parent / ".mplstyle"
OUTPUT_NAME = Path(__file__).with_suffix(".png").name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="age_and_sex",
        description=__doc__,
    )
    parser.add_argument(
        "data", type=Path, help="Path to the data file.",
    )
    args = parser.parse_args()

    data = pd.read_csv(args.data, header=[0, 1, 2])
    output_dir = args.data.parent / "figures"
    output_dir.mkdir(exist_ok=True)

    plt.style.use(MPLSTYLE)
    plt.rcParams.update(figsizes.icml2022_half())
    plt.rcParams.update(fontsizes.icml2022())
    fig, ax = plt.subplots()

    t_stage_labels = ["T1", "T2", "T3", "T4"]
    colors = [
        COLORS["green"],
        COLORS["blue"],
        COLORS["orange"],
        COLORS["red"],
    ]

    if 0 in data[("tumor", "1", "t_stage")].values:
        t_stage_labels = ["T0", *t_stage_labels]
        colors = [COLORS["gray"], *colors]

    tmp = data.groupby(
        ("tumor", "1", "t_stage")
    ).size().plot.pie(
        y=("tumor", "1", "t_stage"),
        ax=ax,
        colors=colors,
        labels=t_stage_labels,
        autopct=create_label,
        counterclock=False,
        startangle=90,
    )

    plt.savefig(output_dir / OUTPUT_NAME, dpi=300)
