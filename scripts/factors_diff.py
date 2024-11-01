"""Plot the difference of clinicopathological factors in two datasets as a bar plot."""

import argparse
from pathlib import Path

import lydata
import matplotlib.pyplot as plt
from lydata import C
from lyscripts.plot.utils import COLORS
from shared import MPLSTYLE
from tueplots import figsizes, fontsizes
from upset_diff import get_parser, kwargs_from_option

OUTPUT_NAME = Path(__file__).with_suffix(".png").name


def create_ax() -> plt.Axes:
    """Create the axis for the plot."""
    plt.style.use(MPLSTYLE)
    plt.rcParams.update(figsizes.icml2022_half())
    plt.rcParams.update(fontsizes.icml2022())
    _, ax = plt.subplots()
    return ax


def main() -> None:
    """Run main routine."""
    args = get_parser().parse_args()

    load_kwargs = {
        "repo": "rmnldwg/lydata",
        "ref": args.commit,
    }

    first_dataset = next(lydata.load_datasets(
        **kwargs_from_option(args.first_dataset),
        **load_kwargs,
    ))
    second_dataset = next(lydata.load_datasets(
        **kwargs_from_option(args.second_dataset),
        **load_kwargs,
    ))

    first_color = COLORS["blue"]
    second_color = COLORS["red"]

    ax = create_ax()
    height = 0.5
    sep = 3 * height
    kwargs = {
        "height": height,
        "alpha": 1,
        "zorder": 2.001,
    }
    yticks = []
    yticklabels = []

    for i, (label, query) in enumerate([
        ("Midline\nextension", C("midext") == True),
        ("Alcohol\nabuse", C("alcohol") == True),
        ("HPV+", C("hpv") == True),
        ("Nicotine\nabuse", C("smoke") == True),
        ("Male", C("sex").isin(["male", "MALE"])),
    ]):
        first_percent = 100 * first_dataset.ly.portion(query=query).ratio
        second_percent = 100 * second_dataset.ly.portion(query=query).ratio

        y = i * sep

        if i == 0:
            first_kwargs = {"label": "USZ", "color": first_color, **kwargs}
            second_kwargs = {"label": "HVH", "color": second_color, **kwargs}
        else:
            first_kwargs = {"color": first_color, **kwargs}
            second_kwargs = {"color": second_color, **kwargs}

        ax.barh(y=y + height/2, width=first_percent, **first_kwargs)
        ax.barh(y=y - height/2, width=second_percent, **second_kwargs)

        yticks.append(y)
        yticklabels.append(label)

    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Percentage of patients (%)")
    ax.legend(loc="lower right")

    output_dir = Path(args.second_dataset) / "figures"
    output_dir.mkdir(exist_ok=True, parents=True)
    plt.savefig(output_dir / OUTPUT_NAME, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
