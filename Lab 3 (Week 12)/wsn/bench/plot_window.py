# FIT3143 Lab 3 - how the base station window (-w) changes its replies
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# Usage: python3 bench/plot_window.py [CSV files or directories ...]   (default results/window)
# Writes window_replies.png and window_summary.csv next to the first input.

import csv
import os
import sys

from plotstyle import BLUE, INK, ORANGE, footnote, load_rows, mean_sd, plt, style


def main():
    inputs = sys.argv[1:] or ['results/window']
    out = inputs[0] if os.path.isdir(inputs[0]) else os.path.dirname(inputs[0]) or '.'
    rows = load_rows(inputs)
    windows = sorted({float(r['window_s']) for r in rows})

    summary = []
    for w in windows:
        sel = [r for r in rows if float(r['window_s']) == w]
        nodes = mean_sd([int(r['replies_nodes']) for r in sel])[0]
        none = mean_sd([int(r['replies_none']) for r in sel])[0]
        pct = [100 * int(r['replies_none']) / int(r['alerts']) for r in sel if int(r['alerts'])]
        summary.append((w, len(sel), nodes, none, mean_sd(pct)[0] if pct else 0.0))

    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
    xs = range(len(windows))
    nodes = [s[2] for s in summary]
    none = [s[3] for s in summary]
    # 2px white edge keeps a gap between the stacked segments
    ax.bar(xs, nodes, 0.6, color=BLUE, edgecolor='white', linewidth=2, label='reply: nearest free nodes', zorder=2)
    ax.bar(xs, none, 0.6, bottom=nodes, color=ORANGE, edgecolor='white', linewidth=2,
           label='reply: no nodes available nearby', zorder=2)
    for x, (_, _, n, k, pct) in zip(xs, summary):
        ax.annotate(f'{pct:.0f}%', (x, n + k), ha='center', va='bottom', fontsize=9, color=INK,
                    xytext=(0, 3), textcoords='offset points')
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f'{w:g}' for w in windows])
    # pad leaves room for the legend row between the title and the plot
    style(ax, 'Base station replies vs window w', 'alerts per run (mean)', 'window w (seconds)', pad=34)
    ax.legend(frameon=False, fontsize=10, loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2,
              labelcolor=INK, borderaxespad=0.2)
    ax.margins(y=0.12)
    r0 = rows[0]
    footnote(fig, f"{r0['m']}x{r0['n']} grid, {float(r0['duration_s']):.0f} s runs, cycle {r0['cycle_ms']} ms, "
                  f"{summary[0][1]} runs per bar; label = share of replies saying no nodes nearby")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(out, 'window_replies.png'))
    plt.close(fig)

    with open(os.path.join(out, 'window_summary.csv'), 'w', newline='') as f:
        wr = csv.writer(f, lineterminator='\n')
        wr.writerow(['window_s', 'runs', 'replies_nodes_mean', 'replies_none_mean', 'none_pct'])
        for s in summary:
            wr.writerow([f'{s[0]:g}', s[1], f'{s[2]:.1f}', f'{s[3]:.1f}', f'{s[4]:.1f}'])

    print(f"{'w (s)':>6}{'with nodes':>12}{'none nearby':>13}{'none %':>8}")
    for w, _, n, k, pct in summary:
        print(f"{w:6g}{n:12.1f}{k:13.1f}{pct:8.1f}")


if __name__ == '__main__':
    main()
