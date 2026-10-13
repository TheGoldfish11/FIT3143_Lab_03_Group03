# FIT3143 Lab 3 - Task 3 graphs: delay of each message type vs grid size and line length
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# Usage: python3 bench/plot_task3.py [CSV files or directories ...]   (default results/task3)
# Rows with m = 1 are lines (Task 3b), the rest are grids (Task 3a). Writes task3_*.png and
# task3_summary.csv next to the first input, and prints how fast each delay grows per node.

import csv
import os
import sys

import numpy as np

from plotstyle import BLUE, INK, MESSAGES, MUTED, ORANGE, footnote, load_rows, mean_sd, plt, style


def by_size(rows, col):
    """{(m, n): [per-run average delay in ms]} for runs that timed at least one message."""
    out = {}
    for r in rows:
        if int(r[col + '_n']) > 0:
            out.setdefault((int(r['m']), int(r['n'])), []).append(float(r[col + '_avg_s']) * 1e3)
    return out


def trend(points):
    """Least-squares slope (ms per node) and intercept through every run."""
    xs = [m * n for (m, n), vals in points.items() for _ in vals]
    ys = [v for vals in points.values() for v in vals]
    if len(set(xs)) < 2:
        return None
    slope, icept = np.polyfit(xs, ys, 1)
    return slope, icept


def draw(ax, points, colour, label, connect):
    sizes = sorted(points, key=lambda s: (s[0] * s[1], s))
    xs = [m * n for m, n in sizes]
    stats = [mean_sd(points[s]) for s in sizes]
    means = [s[0] for s in stats]
    sds = [s[1] for s in stats]
    if connect:
        ax.plot(xs, means, color=colour, linewidth=2, zorder=2)
    ax.errorbar(xs, means, yerr=sds, fmt='o', color=colour, markersize=5, elinewidth=1, capsize=2,
                markeredgecolor='white', markeredgewidth=1, zorder=3, label=label)
    fit = trend(points)
    if fit and not connect:
        lo, hi = min(xs), max(xs)
        ax.plot([lo, hi], [fit[1] + fit[0] * lo, fit[1] + fit[0] * hi], color=colour, linewidth=1.5,
                linestyle='--', zorder=1)
    return fit


def figure(sets, path, note):
    """One panel per message type; sets = [(rows, colour, label, connect)]."""
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), dpi=200)
    for ax, (col, title) in zip(axes, MESSAGES):
        for rows, colour, label, connect in sets:
            draw(ax, by_size(rows, col), colour, label, connect)
        style(ax, title, 'round trip (ms)', 'nodes (m × n)')
        ax.set_ylim(bottom=0)
    if len(sets) > 1:
        axes[0].legend(frameon=False, fontsize=9, loc='upper left', labelcolor=INK)
    footnote(fig, note)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def main():
    inputs = sys.argv[1:] or ['results/task3']
    out = inputs[0] if os.path.isdir(inputs[0]) else os.path.dirname(inputs[0]) or '.'
    rows = load_rows(inputs)
    grids = [r for r in rows if int(r['m']) > 1]
    lines = [r for r in rows if int(r['m']) == 1]
    r0 = rows[0]
    note = (f"{float(r0['duration_s']):.0f} s runs, cycle {r0['cycle_ms']} ms, poll interval {r0['poll_us']} µs, "
            f"base {r0['base_mode']}, nodes {r0['node_mode']}; dots = mean of repeats, whiskers = ±1 SD")

    if grids:
        figure([(grids, BLUE, 'grid', False)], os.path.join(out, 'task3_grids.png'),
               note + ', dashed = least-squares trend')
    if lines:
        figure([(lines, ORANGE, 'line (1 × N)', True)], os.path.join(out, 'task3_lines.png'), note)
    if grids and lines:
        figure([(grids, BLUE, 'grid', False), (lines, ORANGE, 'line (1 × N)', True)],
               os.path.join(out, 'task3_grid_vs_line.png'), note)

    with open(os.path.join(out, 'task3_summary.csv'), 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['topology', 'm', 'n', 'nodes', 'runs'] +
                   [f'{c}_{s}' for c, _ in MESSAGES for s in ('mean_ms', 'sd_ms')])
        for name, rs in (('grid', grids), ('line', lines)):
            per = {c: by_size(rs, c) for c, _ in MESSAGES}
            for size in sorted({(int(r['m']), int(r['n'])) for r in rs}, key=lambda s: (s[0] * s[1], s)):
                cells = []
                for c, _ in MESSAGES:
                    vals = per[c].get(size)
                    cells += [f'{x:.4f}' for x in mean_sd(vals)] if vals else ['', '']
                runs = sum(1 for r in rs if (int(r['m']), int(r['n'])) == size)
                w.writerow([name, size[0], size[1], size[0] * size[1], runs] + cells)

    print('How much each round trip grows per extra node (least-squares slope):')
    for name, rs in (('grid', grids), ('line', lines)):
        if not rs:
            continue
        parts = []
        for c, title in MESSAGES:
            fit = trend(by_size(rs, c))
            parts.append(f"{title}: {fit[0] * 1e3:+.1f} µs/node" if fit else f"{title}: n/a")
        print(f"  {name:5} " + ' | '.join(parts))
    print(f"graphs and task3_summary.csv written to {out}/")


if __name__ == '__main__':
    main()
