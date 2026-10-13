# FIT3143 Lab 3 - shared look for every graph, and CSV loading
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)

import csv
import glob
import os
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

BLUE, ORANGE = '#2a78d6', '#eb6834'   # validated categorical slots 1 and 2
INK, MUTED, GRID = '#1f2430', '#5d6577', '#e3e6ec'

# the three request/reply pairs every run times (CSV column prefix, title)
MESSAGES = [
    ('nbr_rtt', 'Neighbour request → reply'),
    ('report_rtt', 'Report → base station reply'),
    ('term_rtt', 'Terminate → ack'),
]


def load_rows(paths):
    """Rows from CSV files or directories of CSV files (CAAS writes one file per job)."""
    files = []
    for p in paths:
        files += sorted(glob.glob(os.path.join(p, '*.csv'))) if os.path.isdir(p) else [p]
    rows = []
    for f in files:
        rows += list(csv.DictReader(open(f)))
    return rows


def mean_sd(values):
    return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)


def style(ax, title, ylabel, xlabel=None, pad=10):
    ax.set_title(title, loc='left', fontsize=12, fontweight='bold', color=INK, pad=pad)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=10)
    if xlabel:
        ax.set_xlabel(xlabel, color=MUTED, fontsize=10)
    ax.grid(axis='y', color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)


def footnote(fig, text):
    fig.text(0.01, 0.01, text, fontsize=8.5, color=MUTED)
