"""Shared variables and functions for the scripts."""

from pathlib import Path

LNLS = ["I", "II", "III", "IV", "V"]
MPLSTYLE = Path(__file__).parent / ".mplstyle"


def remove_artists(ax):
    """Remove all artists from the axes."""
    for artist in (ax.lines + ax.patches + ax.collections):
        artist.remove()
