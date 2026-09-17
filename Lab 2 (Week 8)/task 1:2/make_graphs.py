#!/usr/bin/env python3
"""
FIT3143 Lab 2 - Task 1
Generates the scaling graphs for the Open MPI prime search.

Run:  python3 make_graphs.py
Output: graphs/*.png (300 dpi, for embedding) and graphs/*.pdf (vector)

All measurements: Apple M5 (4 performance + 6 efficiency cores), Open MPI 5.0.9.
Timer covers the whole program, including the sort and the file write.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# ----------------------------------------------------------------- measurements

# Varying n, at 1 and 4 processes.
# Median of 9 runs for n <= 3e6, 3 runs above.
N       = [1e5,    3e5,    1e6,    3e6,    1e7,    3e7,     1e8]
T_1PROC = [0.0013, 0.0044, 0.0203, 0.0856, 0.4302, 1.9692, 10.6936]
T_4PROC = [0.0029, 0.0067, 0.0201, 0.0458, 0.1591, 0.6581,  3.4018]
# Computed from the full-precision timings, not the rounded values above.
# At n = 1e5 the runtimes are ~1 ms, so rounding them to 4 dp would shift the
# ratio by a whole hundredth (0.44 -> 0.45).
SPEEDUP_N = [0.44, 0.66, 1.01, 1.87, 2.70, 2.99, 3.14]

# Varying process count, at n = 1e7. Median of 5 runs.
PROCS    = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
T_PROCS  = [0.4424, 0.2568, 0.1952, 0.1616,
            0.1678, 0.1623, 0.1697, 0.1656, 0.1722, 0.1739]
SPEEDUP_P = [T_PROCS[0] / t for t in T_PROCS]

PERF_CORES = 4          # M5 performance cores; efficiency cores start after this

# ----------------------------------------------------------------------- style

BLUE   = "#2a78d6"
ORANGE = "#eb6834"
INK    = "#1a1a19"
MUTED  = "#8a8880"
GRID   = "#dcdbd4"

plt.rcParams.update({
    "figure.figsize":    (7.2, 4.4),
    "figure.dpi":        110,
    "savefig.dpi":       300,
    "savefig.bbox":      "tight",
    "font.family":       "sans-serif",
    "font.sans-serif":   ["DejaVu Sans"],
    "font.size":         10.5,
    "axes.titlesize":    12.5,
    "axes.titleweight":  "semibold",
    "axes.labelsize":    10.5,
    "axes.edgecolor":    MUTED,
    "axes.linewidth":    0.9,
    "axes.labelcolor":   INK,
    "axes.titlecolor":   INK,
    "text.color":        INK,
    "xtick.color":       MUTED,
    "ytick.color":       MUTED,
    "xtick.labelcolor":  INK,
    "ytick.labelcolor":  INK,
    "xtick.direction":   "out",
    "ytick.direction":   "out",
    "grid.color":        GRID,
    "grid.linewidth":    0.8,
    "legend.frameon":    False,
    "legend.fontsize":   10,
})

OUT = "graphs"
os.makedirs(OUT, exist_ok=True)


def tidy(ax):
    """Remove the top and right spines and put a light grid behind the data."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, which="major", axis="both", zorder=0)
    ax.set_axisbelow(True)


def save(fig, name):
    for ext in ("png", "pdf"):
        path = os.path.join(OUT, f"{name}.{ext}")
        fig.savefig(path)
    plt.close(fig)
    print(f"  {OUT}/{name}.png  +  .pdf")


def sec_fmt(v, _pos):
    """Axis labels in ms below one second, seconds above."""
    if v >= 1:
        return f"{v:g} s"
    return f"{v * 1000:g} ms"


# --------------------------------------------------- 1. runtime against size

def graph_runtime_vs_n():
    fig, ax = plt.subplots()
    ax.plot(N, T_1PROC, "o-", color=BLUE,   lw=2, ms=6,
            label="1 process", zorder=3)
    ax.plot(N, T_4PROC, "s-", color=ORANGE, lw=2, ms=5.5,
            label="4 processes", zorder=3)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(sec_fmt))
    ax.set_xlabel("n  (search limit)")
    ax.set_ylabel("Runtime")
    ax.set_title("Runtime against problem size")

    # mark where the two lines cross - parallel stops losing here
    ax.axvline(1e6, color=MUTED, ls=":", lw=1.2, zorder=1)
    ax.annotate("lines cross\nnear $n=10^6$", xy=(1e6, 0.0203),
                xytext=(1.9e6, 0.0032), fontsize=9, color=MUTED,
                ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9))

    tidy(ax)
    ax.legend(loc="upper left")
    save(fig, "1_runtime_vs_n")


# -------------------------------------------------- 2. speedup against size

def graph_speedup_vs_n():
    fig, ax = plt.subplots()
    ax.axhline(1.0, color=MUTED, ls="--", lw=1.3, zorder=1)
    ax.text(1.25e8, 1.06, "break-even (1×)", fontsize=9,
            color=MUTED, ha="right", va="bottom")

    ax.plot(N, SPEEDUP_N, "o-", color=BLUE, lw=2, ms=6, zorder=3)

    for i in (0, len(N) - 1):
        ax.annotate(f"{SPEEDUP_N[i]:.2f}×", xy=(N[i], SPEEDUP_N[i]),
                    xytext=(0, 11), textcoords="offset points",
                    ha="center", fontsize=10, fontweight="semibold")

    ax.set_xscale("log")
    ax.set_ylim(0, 4)
    ax.set_xlabel("n  (search limit)")
    ax.set_ylabel("Speedup over 1 process")
    ax.set_title("Speedup against problem size  (4 processes)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g}×"))

    tidy(ax)
    save(fig, "2_speedup_vs_n")


# ----------------------------------------- 3. speedup against process count

def graph_speedup_vs_procs():
    fig, ax = plt.subplots()

    # everything past the performance-core count runs partly on efficiency cores
    ax.axvspan(PERF_CORES + 0.5, 10.5, color=ORANGE, alpha=0.06, zorder=0)
    ax.axvline(PERF_CORES + 0.5, color=ORANGE, ls=":", lw=1.3, zorder=1)
    ax.text(PERF_CORES + 0.72, 4.35, "efficiency cores in use",
            fontsize=9, color=ORANGE, va="top")

    ax.plot(PROCS, PROCS, "--", color=MUTED, lw=1.3,
            label="Ideal (linear)", zorder=2)
    ax.plot(PROCS, SPEEDUP_P, "o-", color=BLUE, lw=2, ms=6,
            label="Measured", zorder=3)

    peak = max(range(len(PROCS)), key=lambda i: SPEEDUP_P[i])
    ax.annotate(f"{SPEEDUP_P[peak]:.2f}× at {PROCS[peak]} processes",
                xy=(PROCS[peak], SPEEDUP_P[peak]),
                xytext=(PROCS[peak] + 0.55, SPEEDUP_P[peak] + 0.75),
                fontsize=9.5,
                arrowprops=dict(arrowstyle="->", color=INK, lw=1))

    ax.set_xticks(PROCS)
    ax.set_xlim(0.5, 10.5)
    ax.set_ylim(0, 4.6)
    ax.set_xlabel("MPI processes")
    ax.set_ylabel("Speedup over 1 process")
    ax.set_title("Speedup against process count  ($n=10^7$)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g}×"))

    tidy(ax)
    ax.legend(loc="lower right")
    save(fig, "3_speedup_vs_processes")



# ------------------------------------------------- Lab 1 vs Lab 2 comparison
#
# Convention A: every timer spans "start of work" -> "output written".
# The POSIX Threads implementation as submitted stops its clock after
# pthread_join, excluding the file write; a copy was instrumented to match the
# other three. See the methodology note in the report.
#
# pthreads  : contiguous block split      (Lab 1 Task2, normalised)
# OpenMP    : schedule(dynamic, 1000)     (Lab 1 Task3)
# MPI       : static block-cyclic, 8/proc (Lab 2 task1)

# --- varying n, 4 workers throughout (median of 3) ---
CMP_N       = [1e5,    3e5,    1e6,    3e6,    1e7,    3e7,     1e8]
CMP_SERIAL  = [0.0015, 0.0044, 0.0202, 0.0854, 0.4383, 2.0065, 10.8990]
CMP_PTHREAD = [0.0010, 0.0026, 0.0106, 0.0395, 0.1994, 0.8750,  4.6805]
CMP_OPENMP  = [0.0009, 0.0022, 0.0082, 0.0310, 0.1402, 0.6009,  3.1319]
CMP_MPI     = [0.0028, 0.0099, 0.0172, 0.0411, 0.1581, 0.6617,  3.4063]

# --- varying worker count, n = 1e7 (median of 5) ---
CMP_W        = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
CMP_W_BASE   = 0.436058                       # serial baseline, same n
CMP_W_PTHREAD = [0.5099, 0.3292, 0.2442, 0.1952, 0.1763,
                 0.1710, 0.1566, 0.1507, 0.1462, 0.1472]
CMP_W_OPENMP  = [0.4402, 0.2394, 0.1778, 0.1414, 0.1375,
                 0.1339, 0.1294, 0.1268, 0.1248, 0.1201]
CMP_W_MPI     = [0.4344, 0.2547, 0.1959, 0.1577, 0.1632,
                 0.1572, 0.1568, 0.1587, 0.1804, 0.1671]

# --- linearly spaced n, 4 workers (best of 2) - for the linear-axis graph.
# Sampled on a linear grid rather than reusing the log-spaced points above,
# so the data is evenly distributed across a linear x-axis.
LIN_N       = [10e6, 20e6, 30e6, 40e6, 50e6, 60e6, 70e6, 80e6, 90e6, 100e6]
LIN_SERIAL  = [0.441351, 1.145078, 2.035522, 3.005404, 4.096495,
               5.338598, 6.576341, 7.949114, 9.529862, 11.133160]
LIN_PTHREAD = [0.196223, 0.504804, 0.880995, 1.307170, 1.773418,
               2.286169, 2.849173, 3.440839, 4.071360,  4.738315]
LIN_OPENMP  = [0.141282, 0.353160, 0.601118, 0.888995, 1.208001,
               1.541710, 1.905891, 2.295230, 2.716778,  3.122095]
LIN_MPI     = [0.156187, 0.386550, 0.651766, 0.955455, 1.302453,
               1.667733, 2.055876, 2.499860, 2.898015,  3.366466]

AQUA = "#1baf7a"

# Each series carries a distinct marker as well as a colour, so the three are
# still separable in greyscale or for a colour-blind reader.
STYLE = {
    "pthreads": dict(color=AQUA,   marker="^", label="POSIX Threads"),
    "OpenMP":   dict(color=ORANGE, marker="s", label="OpenMP"),
    "MPI":      dict(color=BLUE,   marker="o", label="Open MPI"),
}


def _speedups(base, times):
    return [b / t for b, t in zip(base, times)]


# ------------------------------------- 4. runtime, all implementations vs n

def graph_cmp_runtime():
    fig, ax = plt.subplots()
    ax.plot(CMP_N, CMP_SERIAL, "--", color=MUTED, lw=1.4,
            label="Serial (1 core)", zorder=2)
    for key, ys in (("pthreads", CMP_PTHREAD),
                    ("OpenMP",   CMP_OPENMP),
                    ("MPI",      CMP_MPI)):
        st = STYLE[key]
        ax.plot(CMP_N, ys, "-", color=st["color"], marker=st["marker"],
                lw=2, ms=5.5, label=st["label"], zorder=3)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(sec_fmt))
    ax.set_xlabel("n  (search limit)")
    ax.set_ylabel("Runtime")
    ax.set_title("Runtime against problem size  (4 workers)")
    tidy(ax)
    ax.legend(loc="upper left")
    save(fig, "4_cmp_runtime_vs_n")


# ------------------------------------- 5. speedup, all implementations vs n

def graph_cmp_speedup_n():
    fig, ax = plt.subplots()
    ax.axhline(1.0, color=MUTED, ls="--", lw=1.3, zorder=1)
    ax.text(1.3e8, 1.05, "break-even (1×)", fontsize=9,
            color=MUTED, ha="right", va="bottom")

    for key, ys in (("pthreads", CMP_PTHREAD),
                    ("OpenMP",   CMP_OPENMP),
                    ("MPI",      CMP_MPI)):
        st = STYLE[key]
        sp = _speedups(CMP_SERIAL, ys)
        ax.plot(CMP_N, sp, "-", color=st["color"], marker=st["marker"],
                lw=2, ms=5.5, label=st["label"], zorder=3)
        # direct end-label: identity never rests on colour alone
        ax.annotate(f"{sp[-1]:.2f}×", xy=(CMP_N[-1], sp[-1]),
                    xytext=(7, -3), textcoords="offset points",
                    color=st["color"], fontsize=9.5, fontweight="semibold",
                    va="center")

    ax.set_xscale("log")
    ax.set_ylim(0, 4)
    ax.set_xlim(7e4, 2.6e8)
    ax.set_xlabel("n  (search limit)")
    ax.set_ylabel("Speedup over serial")
    ax.set_title("Speedup against problem size  (4 workers)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g}×"))
    tidy(ax)
    ax.legend(loc="lower right")
    save(fig, "5_cmp_speedup_vs_n")


# ------------------------- 6. speedup, all implementations vs worker count

def graph_cmp_speedup_workers():
    fig, ax = plt.subplots()
    ax.axvspan(PERF_CORES + 0.5, 10.5, color=ORANGE, alpha=0.06, zorder=0)
    ax.axvline(PERF_CORES + 0.5, color=MUTED, ls=":", lw=1.2, zorder=1)
    ax.text(PERF_CORES + 0.7, 4.32, "efficiency cores in use",
            fontsize=9, color=MUTED, va="top")

    ax.plot(CMP_W, CMP_W, "--", color=MUTED, lw=1.3,
            label="Ideal (linear)", zorder=2)
    for key, ys in (("pthreads", CMP_W_PTHREAD),
                    ("OpenMP",   CMP_W_OPENMP),
                    ("MPI",      CMP_W_MPI)):
        st = STYLE[key]
        sp = [CMP_W_BASE / t for t in ys]
        ax.plot(CMP_W, sp, "-", color=st["color"], marker=st["marker"],
                lw=2, ms=5.5, label=st["label"], zorder=3)
        ax.annotate(f"{sp[-1]:.2f}×", xy=(CMP_W[-1], sp[-1]),
                    xytext=(7, 0), textcoords="offset points",
                    color=st["color"], fontsize=9.5, fontweight="semibold",
                    va="center")

    ax.set_xticks(CMP_W)
    ax.set_xlim(0.5, 11.4)
    ax.set_ylim(0, 4.6)
    ax.set_xlabel("Worker count  (MPI processes / threads)")
    ax.set_ylabel("Speedup over serial")
    ax.set_title("Speedup against worker count  ($n=10^7$)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g}×"))
    tidy(ax)
    ax.legend(loc="lower right", ncol=2)
    save(fig, "6_cmp_speedup_vs_workers")



# --------------------------- 4b. same comparison, linear axes

def graph_cmp_runtime_linear():
    fig, ax = plt.subplots()
    ax.plot(LIN_N, LIN_SERIAL, "--", color=MUTED, lw=1.4,
            label="Serial (1 core)", zorder=2)
    for key, ys in (("pthreads", LIN_PTHREAD),
                    ("OpenMP",   LIN_OPENMP),
                    ("MPI",      LIN_MPI)):
        st = STYLE[key]
        ax.plot(LIN_N, ys, "-", color=st["color"], marker=st["marker"],
                lw=2, ms=5.5, label=st["label"], zorder=3)
        ax.annotate(f"{ys[-1]:.2f} s", xy=(LIN_N[-1], ys[-1]),
                    xytext=(7, 0), textcoords="offset points",
                    color=st["color"], fontsize=9.5, fontweight="semibold",
                    va="center")
    ax.annotate(f"{LIN_SERIAL[-1]:.2f} s", xy=(LIN_N[-1], LIN_SERIAL[-1]),
                xytext=(7, 0), textcoords="offset points",
                color=MUTED, fontsize=9.5, va="center")

    ax.set_xlim(0, 1.12e8)
    ax.set_ylim(0, 11.9)
    ax.set_xticks([0, 2e7, 4e7, 6e7, 8e7, 1e8])
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda v, p: "0" if v == 0 else f"{v/1e6:g}M"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g} s"))
    ax.set_xlabel("n  (search limit)")
    ax.set_ylabel("Runtime")
    ax.set_title("Runtime against problem size  (4 workers, linear axes)")
    tidy(ax)
    ax.legend(loc="upper left")
    save(fig, "4b_cmp_runtime_vs_n_linear")


if __name__ == "__main__":
    print("Writing graphs:")
    graph_runtime_vs_n()
    graph_speedup_vs_n()
    graph_speedup_vs_procs()
    graph_cmp_runtime()
    graph_cmp_runtime_linear()
    graph_cmp_speedup_n()
    graph_cmp_speedup_workers()
    print("Done.")
