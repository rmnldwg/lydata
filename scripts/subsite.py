"""
Plot the distribution over primary tumor subsites.
"""
from pathlib import Path
import argparse
import re
import textwrap

import pandas as pd
import matplotlib.pyplot as plt

from lyscripts.plot.utils import get_size, COLORS


MPLSTYLE = Path(__file__).parent / ".mplstyle"
OUTPUT_NAME = Path(__file__).with_suffix(".png").name
SUBSITES = {
    "C00": "lips",
    "C01": "base of tongue",
    "C02": "other & unspec. parts of tongue",
    "C03": "gum",
    "C04": "floor of mouth",
    "C05": "palate",
    "C06": "other & unspec. parts of mouth",
    "C07": "parotid gland",
    "C08": "other & unspec. major salivary glands",
    "C09": "tonsil",
    "C10": "oropharynx",
    "C11": "nasopharynx",
    "C12": "pyriform sinus",
    "C13": "hypopharynx",
    "C14": "other/ill-defined sites in the lip, oral cavity and pharynx",
    "C32": "larynx",
}


def group_icd_codex(icd):
    """Group ICD codes to their parent blocks."""
    match = re.match(r"(C\d\d)", icd)
    return match.group(1)


def icd_to_subsite(icd):
    """Convert an ICD code to a subsite."""
    match = re.match(r"(C\d\d)", icd)
    return "\n".join(textwrap.wrap(SUBSITES[match.group(1)], width=22))


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

    subsites = data[("tumor", "1", "subsite")].map(group_icd_codex)
    subsites = subsites.value_counts()
    subsites.index = subsites.index.map(icd_to_subsite)

    plt.style.use(MPLSTYLE)
    fig, ax = plt.subplots(figsize=get_size(), constrained_layout=True)

    subsites.plot.barh(
        ax=ax,
        color=COLORS["blue"],
        xlabel="Number of patients",
        ylabel="",
    )
    ax.set_yticklabels(subsites.index, fontsize=6, linespacing=0.75)

    plt.savefig(output_dir / OUTPUT_NAME, dpi=300)
