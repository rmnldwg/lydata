"""
Create a bar plot of different filters applied to the dataset, illustrating how
the patient-individual data may be used.
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tueplots import figsizes, fontsizes

MPLSTYLE = Path(__file__).parent / ".mplstyle"
OUTPUT_NAME = Path(__file__).with_suffix(".png").name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="bar_plot",
        description=__doc__,
    )
    parser.add_argument(
        "data", type=Path, help="Path to the data file.",
    )
    args = parser.parse_args()

    plt.style.use(MPLSTYLE)
    plt.rcParams.update(figsizes.icml2022_half(
        nrows=1, ncols=1, height_to_width_ratio=0.75,
    ))
    plt.rcParams.update(fontsizes.icml2022())
    fig, ax = plt.subplots()

    data = pd.read_csv(args.data, header=[0, 1, 2])
    output_dir = args.data.parent / "figures"
    output_dir.mkdir(exist_ok=True)

    has_lnl_II = False
    for lnl in ["II", "IIa", "IIb"]:
        if lnl in data["pathology", "ipsi"]:
            has_lnl_II = has_lnl_II | (data["pathology", "ipsi", lnl] == True)
    has_lnl_III = data["pathology", "ipsi", "III"] == True

    scenarios = {
        "overall": True,
        "HPV pos": data["patient", "#", "hpv_status"] == True,
        "HPV neg": data["patient", "#", "hpv_status"] == False,
        "smoker": data["patient", "#", "nicotine_abuse"] == True,
        "non-smoker": data["patient", "#", "nicotine_abuse"] == False,
        "alcohol": data["patient", "#", "alcohol_abuse"] == True,
        "non-alcohol": data["patient", "#", "alcohol_abuse"] == False,
        "LNL II pos": has_lnl_II,
        "LNL II neg": ~has_lnl_II,
    }

    left = np.zeros(len(scenarios))
    positions = - np.array([0, 2,3, 5,6, 8,9, 11,12])
    for i, t_stage in enumerate([1, 2, 3, 4]):
        is_t_stage = data["tumor", "1", "t_stage"] == t_stage
        right = left.copy()
        for j, condition in enumerate(scenarios.values()):
            subset = data.loc[is_t_stage & has_lnl_III & condition]
            total = data.loc[is_t_stage & condition]
            right[j] += 100 * len(subset) / len(total)

        ax.barh(
            positions,
            right - left,
            left=left,
            label=f"T{t_stage}",
        )
        left = right

    ax.set_yticks(positions)
    ax.set_yticklabels(scenarios.keys())
    ax.set_xlabel("Percentage of ipsilateral LNL III involvement")
    ax.legend(title="T-category")

    plt.savefig(output_dir / OUTPUT_NAME, dpi=300)
