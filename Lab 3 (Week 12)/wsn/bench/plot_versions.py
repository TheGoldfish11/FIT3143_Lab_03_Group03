# FIT3143 Lab 3 - graphs and a table from bench_versions.sh results
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# Usage: python3 bench/plot_versions.py [CSV file or directory of CSVs] [output directory]
# Needs matplotlib (pip install matplotlib). Writes versions_*.png and versions_summary.csv.

import csv
import os
import statistics
import sys

from plotstyle import load_rows, plt

BASE_MODES = ['poll', 'block', 'irecv']
NODE_MODES = ['nonblock', 'block']
BASE_LABELS = {'poll': 'poll\nIprobe + sleep', 'block': 'block\nProbe (waits)', 'irecv': 'irecv\nIrecv + Testany'}
NODE_LABELS = {'nonblock': 'nodes: non-blocking', 'block': 'nodes: blocking'}
COLOURS = {'nonblock': '#2a78d6', 'block': '#eb6834'}   # validated categorical slots 1 and 2
INK, MUTED, GRID = '#1f2430', '#5d6577', '#e3e6ec'

METRICS = [
    # column, title, unit label, scale
    ('report_rtt_avg_s', 'Report round trip (REPORT → BASE_REPLY)', 'milliseconds', 1e3),
    ('nbr_rtt_avg_s', 'Neighbour round trip (NBR_REQ → NBR_RESP)', 'milliseconds', 1e3),
    ('base_cpu_pct', 'Base station CPU use', '% of one core', 1),
    ('node_ctrl_cpu_avg_s', 'Node MPI thread CPU time (per node)', 'seconds', 1),
]


def load(path):
    rows = load_rows([path])
    for r in rows:
        r['base_cpu_pct'] = 100 * float(r['base_cpu_s']) / float(r['sim_time_s'])
    return rows


def summarise(rows):
    out = {}
    for b in BASE_MODES:
        for n in NODE_MODES:
            sel = [r for r in rows if r['base_mode'] == b and r['node_mode'] == n]
            if not sel:
                continue
            out[(b, n)] = {}
            for col, _, _, scale in METRICS + [('main_overrun_s', '', '', 1e3), ('shutdown_s', '', '', 1e3),
                                               ('alerts', '', '', 1), ('base_idle_wakeups', '', '', 1)]:
                vals = [float(r[col]) * scale for r in sel]
                out[(b, n)][col] = (statistics.mean(vals), statistics.stdev(vals) if len(vals) > 1 else 0.0,
                                    len(vals))
    return out


def style(ax, title, unit):
    ax.set_title(title, loc='left', fontsize=13, fontweight='bold', color=INK, pad=34)
    ax.set_ylabel(unit, color=MUTED, fontsize=11)
    ax.grid(axis='y', color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)


def bar_chart(summary, col, title, unit, path, note):
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
    width, gap = 0.36, 0.02
    for j, n in enumerate(NODE_MODES):
        xs, means, errs = [], [], []
        for i, b in enumerate(BASE_MODES):
            if (b, n) not in summary:
                continue
            m, sd, _ = summary[(b, n)][col]
            xs.append(i + (j - 0.5) * (width + gap))
            means.append(m)
            errs.append(sd)
        bars = ax.bar(xs, means, width, color=COLOURS[n], label=NODE_LABELS[n], zorder=2)
        ax.errorbar(xs, means, yerr=errs, fmt='none', ecolor=INK, elinewidth=1, capsize=3, zorder=3)
        for x, m, e in zip(xs, means, errs):
            ax.annotate(f'{m:.2f}', (x, m + e), ha='center', va='bottom', fontsize=9, color=INK,
                        xytext=(0, 3), textcoords='offset points')
    ax.set_xticks(range(len(BASE_MODES)))
    ax.set_xticklabels([BASE_LABELS[b] for b in BASE_MODES], color=INK)
    ax.set_xlabel('base station version', color=MUTED, fontsize=11, labelpad=8)
    ax.set_ylim(bottom=0)
    ax.margins(y=0.15)
    style(ax, title, unit)
    # legend sits in its own row between the title and the plot, clear of tall bars
    ax.legend(frameon=False, fontsize=10, loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2,
              labelcolor=INK, borderaxespad=0.2)
    fig.text(0.01, 0.01, note, fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else 'results/versions.csv'
    out = sys.argv[2] if len(sys.argv) > 2 else (src if os.path.isdir(src) else os.path.dirname(src) or '.')
    rows = load(src)
    summary = summarise(rows)
    r0 = rows[0]
    runs = min(v['alerts'][2] for v in summary.values())
    note = (f"{r0['m']}x{r0['n']} grid, {float(r0['duration_s']):.0f} s runs, cycle {r0['cycle_ms']} ms, "
            f"poll interval {r0['poll_us']} µs, {runs} runs per bar; bars = mean, whiskers = ±1 standard deviation")

    names = ['report_rtt', 'nbr_rtt', 'base_cpu', 'node_cpu']
    for (col, title, unit, _), name in zip(METRICS, names):
        bar_chart(summary, col, title, unit, os.path.join(out, f'versions_{name}.png'), note)

    with open(os.path.join(out, 'versions_summary.csv'), 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['base_mode', 'node_mode', 'runs', 'report_rtt_ms', 'nbr_rtt_ms', 'base_cpu_pct',
                    'node_cpu_s', 'main_overrun_ms', 'shutdown_ms', 'alerts', 'base_idle_polls'])
        for (b, n), v in summary.items():
            w.writerow([b, n, v['alerts'][2]] + [f'{v[c][0]:.3f}' for c in
                       ['report_rtt_avg_s', 'nbr_rtt_avg_s', 'base_cpu_pct', 'node_ctrl_cpu_avg_s',
                        'main_overrun_s', 'shutdown_s', 'alerts', 'base_idle_wakeups']])

    print(f"{'version':18}{'report ms':>10}{'nbr ms':>8}{'base CPU %':>11}{'overrun ms':>11}{'shutdown ms':>12}")
    for (b, n), v in summary.items():
        print(f"{b + ' / ' + n:18}{v['report_rtt_avg_s'][0]:10.3f}{v['nbr_rtt_avg_s'][0]:8.3f}"
              f"{v['base_cpu_pct'][0]:11.1f}{v['main_overrun_s'][0]:11.1f}{v['shutdown_s'][0]:12.1f}")


if __name__ == '__main__':
    main()
