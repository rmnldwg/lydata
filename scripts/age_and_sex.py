"""
Plot the distribution over patient's age, stratified by biological sex and somking
status.
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lyscripts.plot.utils import COLORS
from tueplots import figsizes, fontsizes

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


    male_ages = data.loc[
        data[("patient", "#", "sex")] == "male",
        ("patient", "#", "age")
    ].values
    male_smoker_ages = data.loc[
        (data[("patient", "#", "sex")] == "male")
        & data[("patient", "#", "nicotine_abuse")],
        ("patient", "#", "age")
    ]
    male_percent = 100 * len(male_ages) / len(data)
    male_smoker_percent = 100 * len(male_smoker_ages) / len(data)

    female_ages = data.loc[
        data[("patient", "#", "sex")] == "female",
        ("patient", "#", "age")
    ].values
    female_smoker_ages = data.loc[
        (data[("patient", "#", "sex")] == "female")
        & data[("patient", "#", "nicotine_abuse")],
        ("patient", "#", "age")
    ]
    female_percent = 100 * len(female_ages) / len(data)
    female_smoker_percent = 100 * len(female_smoker_ages) / len(data)

    bins = np.linspace(0, 100, 21)
    hist_kwargs = {
        "bins": bins,
        "orientation": "horizontal",
        "zorder": 4,
    }

    plt.style.use(MPLSTYLE)
    plt.rcParams.update(figsizes.icml2022_full(
        nrows=1, ncols=2, height_to_width_ratio=0.75,
    ))
    plt.rcParams.update(fontsizes.icml2022())
    fig, ax = plt.subplots(1,2, sharey=True)

    ax[0].hist(
        male_ages,
        label=f"male ({male_percent:.1f}%)",
        color=COLORS["blue"], histtype="stepfilled", **hist_kwargs
    )
    ax[0].hist(
        male_smoker_ages,
        label=f"smokers ({male_smoker_percent:.1f}%)",
        color="black", histtype="step", hatch="////", **hist_kwargs
    )

    male_xlim = ax[0].get_xlim()
    ax[0].set_xlim(male_xlim[::-1])
    ax[0].set_ylim([0, 100])
    ax[0].yaxis.tick_right()
    ax[0].set_yticks(np.linspace(10,90,5))
    ax[0].set_yticks(np.linspace(20,100,5), minor=True)
    ax[0].set_yticklabels(np.linspace(10,90,5, dtype=int))
    ax[0].tick_params(axis="y", pad=7)
    ax[0].legend(loc="lower left")


    ax[1].hist(
        female_ages,
        label=f"female ({female_percent:.1f}%)",
        color=COLORS["red"], histtype="stepfilled", **hist_kwargs
    )
    ax[1].hist(
        female_smoker_ages,
        label=f"smokers ({female_smoker_percent:.1f}%)",
        color="black", histtype="step", hatch="////", **hist_kwargs
    )

    ax[1].set_xlim(male_xlim)
    ax[1].legend(loc="lower right")

    fig.supxlabel("number of patients", fontweight="normal", fontsize="medium")

    plt.savefig(output_dir / OUTPUT_NAME, dpi=300)
