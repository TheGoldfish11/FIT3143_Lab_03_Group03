#!/usr/bin/env python3
"""
FIT3143 Lab 2 - graphs from the CAAS cluster runs.
Machine: Monash CAAS, 14 nodes x 16-core AMD EPYC, Gigabit ethernet, SLURM.
Run:  python3 caas_graphs.py      Output: graphs_caas/*.png and *.pdf
"""
import os, csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
VIOLET, INK, MUTED, GRID = "#4a3aa7", "#1a1a19", "#8a8880", "#dcdbd4"
OUT = "graphs_caas"
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "figure.figsize": (7.2, 4.4), "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"], "font.size": 10.5,
    "axes.titlesize": 12.5, "axes.titleweight": "semibold",
    "axes.edgecolor": MUTED, "axes.linewidth": 0.9,
    "axes.labelcolor": INK, "axes.titlecolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": INK, "ytick.labelcolor": INK,
    "grid.color": GRID, "grid.linewidth": 0.8, "legend.frameon": False,
})

def rd(p):
    with open(os.path.join("caas_results", p)) as f:
        return list(csv.DictReader(f))
def fl(v):
    try: return float(v)
    except (TypeError, ValueError): return None

SERIAL_40M = 14.559253
STYLE = {
    "pthreads": dict(color=AQUA,   marker="^", label="POSIX Threads"),
    "openmp":   dict(color=ORANGE, marker="s", label="OpenMP"),
    "mpi":      dict(color=BLUE,   marker="o", label="Open MPI (Task 1)"),
    "hybrid":   dict(color=VIOLET, marker="D", label="Hybrid MPI+OpenMP (Task 2)"),
}
def tidy(ax):
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.grid(True, zorder=0); ax.set_axisbelow(True)
def save(fig, name):
    for e in ("png", "pdf"): fig.savefig(os.path.join(OUT, f"{name}.{e}"))
    plt.close(fig); print(f"  {OUT}/{name}.png + .pdf")
xfmt = FuncFormatter(lambda v, p: f"{v/1e6:g}M")
sfmt = FuncFormatter(lambda v, p: f"{v:g}x")

sh  = rd("results_shared_med.csv")   # median of 3 reps
mh  = rd("results_mpi_med.csv")      # median of 3 reps
wk  = rd("workers.csv");   hy = rd("hybrid_splits.csv")
NS  = [float(r["n"]) for r in sh]
SER = [float(r["serial"]) for r in sh]

# ---- graph 1: runtime vs n, everything at 16 workers ----
def g1():
    fig, ax = plt.subplots()
    # the serial line is omitted: at 37 s it is ~10x the parallel runs and
    # compresses them into an unreadable band. Its values are in graph 2 as
    # the speedup baseline, and in the results table.
    for key, col in (("pthreads", "pthreads16"), ("openmp", "openmp16")):
        st = STYLE[key]
        ax.plot(NS, [float(r[col]) for r in sh], "-", color=st["color"],
                marker=st["marker"], lw=2, ms=4.5, label=st["label"])
    for key, col in (("mpi", "mpi16"), ("hybrid", "hybrid16")):
        st = STYLE[key]
        ax.plot(NS, [float(r[col]) for r in mh], "-", color=st["color"],
                marker=st["marker"], lw=2, ms=4.5, label=st["label"])
    ax.xaxis.set_major_formatter(xfmt)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p: f"{v:g} s"))
    ax.set_xlabel("n  (search limit)"); ax.set_ylabel("Runtime")
    ax.set_title("Runtime against problem size  (16 workers, CAAS, median of 3)")
    ax.set_ylim(0, 3.6)
    ax.annotate("serial at $n=7.8\\times10^7$ is 37.6 s,\nabout 12x the slowest line here",
                xy=(0.02, 0.94), xycoords="axes fraction", fontsize=8.5, color=MUTED,
                va="top")
    tidy(ax); ax.legend(loc="lower right")
    save(fig, "caas_1_runtime_vs_n")

# ---- graph 2: speedup vs n ----
def g2():
    fig, ax = plt.subplots()
    for key, rows, col in (("pthreads", sh, "pthreads16"), ("openmp", sh, "openmp16"),
                           ("mpi", mh, "mpi16"), ("hybrid", mh, "hybrid16")):
        st = STYLE[key]
        sp = [s/float(r[col]) for s, r in zip(SER, rows)]
        ax.plot(NS, sp, "-", color=st["color"], marker=st["marker"],
                lw=2, ms=4.5, label=st["label"])
    ax.axhline(16, color=MUTED, ls=":", lw=1.2)
    ax.text(NS[-1], 16.3, "16 workers (ideal)", fontsize=9, color=MUTED, ha="right")
    ax.xaxis.set_major_formatter(xfmt); ax.yaxis.set_major_formatter(sfmt)
    ax.set_xlabel("n  (search limit)"); ax.set_ylabel("Speedup over serial")
    ax.set_title("Speedup against problem size  (16 workers, CAAS, median of 3)")
    ax.set_ylim(0, 18); tidy(ax); ax.legend(loc="lower right", ncol=2, fontsize=9)
    save(fig, "caas_2_speedup_vs_n")

# ---- graph 3: speedup vs worker count; threads cannot leave one node ----
def g3():
    fig, ax = plt.subplots()
    ax.axvspan(16.5, 33, color=BLUE, alpha=0.05, zorder=0)
    ax.text(17.2, 16.8, "beyond one node\n(shared memory cannot reach here)",
            fontsize=9, color=MUTED, va="top")
    W = [int(r["workers"]) for r in wk]
    ax.plot([1, 32], [1, 32], "--", color=MUTED, lw=1.3, label="Ideal (linear)")
    for key in ("pthreads", "openmp", "mpi"):
        st = STYLE[key]
        xs = [w for w, r in zip(W, wk) if fl(r[key])]
        ys = [SERIAL_40M/float(r[key]) for r in wk if fl(r[key])]
        ax.plot(xs, ys, "-", color=st["color"], marker=st["marker"],
                lw=2, ms=5.5, label=st["label"])
    best = {}
    for r in hy:
        w = int(r["workers"]); t = float(r["seconds"])
        if w not in best or t < best[w]: best[w] = t
    xs = sorted(best); st = STYLE["hybrid"]
    ax.plot(xs, [SERIAL_40M/best[w] for w in xs], "-", color=st["color"],
            marker=st["marker"], lw=2, ms=5.5, label=st["label"])
    ax.annotate("16 procs on a 16-core node:\nno core left for the OS",
                xy=(16, SERIAL_40M/2.179464), xytext=(6.5, 3.4), fontsize=8.5,
                color=INK, arrowprops=dict(arrowstyle="->", color=INK, lw=0.9))
    ax.set_xticks([1,4,8,12,16,20,24,28,32]); ax.set_xlim(0, 33); ax.set_ylim(0, 22)
    ax.yaxis.set_major_formatter(sfmt)
    ax.set_xlabel("Worker count  (processes x threads)")
    ax.set_ylabel("Speedup over serial")
    ax.set_title("Speedup against worker count  ($n=4\\times10^7$, CAAS)")
    tidy(ax); ax.legend(loc="upper left", fontsize=9)
    save(fig, "caas_3_speedup_vs_workers")

# ---- graph 4: hybrid split at matched worker counts ----
def g4():
    fig, ax = plt.subplots()
    groups = sorted({int(r["workers"]) for r in hy})
    for gi, w in enumerate(groups):
        rows = sorted([r for r in hy if int(r["workers"]) == w],
                      key=lambda r: int(r["procs"]))
        xs = list(range(len(rows)))
        ys = [SERIAL_40M/float(r["seconds"]) for r in rows]
        off = gi * 0.0
        ax.plot([x + off for x in xs], ys, "-o", lw=1.8, ms=5,
                label=f"{w} workers")
        for x, y, r in zip(xs, ys, rows):
            ax.annotate(f"{r['procs']}x{r['threads']}", xy=(x, y),
                        xytext=(0, 7), textcoords="offset points",
                        ha="center", fontsize=7.5, color=MUTED)
    ax.set_xticks([]); ax.yaxis.set_major_formatter(sfmt)
    ax.set_xlabel("process x thread split  (most MPI-heavy on the right)")
    ax.set_ylabel("Speedup over serial")
    ax.set_title("Hybrid: does the process/thread split matter?  ($n=4\\times10^7$)")
    tidy(ax); ax.legend(loc="upper left", fontsize=9, ncol=2)
    save(fig, "caas_4_hybrid_splits")

# ---- graphs 6 & 7: empirical vs Amdahl ----
def karp_flatt(sp, p):
    return (1/sp - 1/p) / (1 - 1/p) if p > 1 else None
def amdahl(f, p): return 1.0/(f + (1-f)/p)

def g67():
    for name, pairs, title, fname in (
        ("Open MPI (Task 1)",
         [(int(r["workers"]), float(r["mpi"])) for r in wk if fl(r["mpi"])],
         "Empirical vs theoretical speedup - Open MPI", "caas_6_amdahl_mpi"),
        ("Hybrid (Task 2)",
         sorted({int(r["workers"]): min(float(x["seconds"]) for x in hy
                 if int(x["workers"]) == int(r["workers"]))
                 for r in hy}.items()),
         "Empirical vs theoretical speedup - Hybrid MPI+OpenMP", "caas_7_amdahl_hybrid"),
    ):
        ps  = [p for p, t in pairs]
        sps = [SERIAL_40M/t for p, t in pairs]
        # fit the serial fraction from the largest well-behaved measurement
        cand = [(p, s) for p, s in zip(ps, sps) if p >= 8]
        p_fit, s_fit = max(cand, key=lambda ps_: ps_[1])
        f = karp_flatt(s_fit, p_fit)
        fig, ax = plt.subplots()
        grid = list(range(1, 33))
        ax.plot(grid, [amdahl(f, p) for p in grid], "--", color=MUTED, lw=1.6,
                label=f"Amdahl, f = {f:.3f}")
        ax.plot(grid, grid, ":", color=MUTED, lw=1.1, label="Ideal (linear)")
        col = BLUE if "MPI (" in name else VIOLET
        mk  = "o" if "MPI (" in name else "D"
        ax.plot(ps, sps, "-", color=col, marker=mk, lw=2, ms=5.5, label="Measured")
        ax.axhline(1/f, color=col, ls=":", lw=1.1)
        ax.text(1, 1/f + 0.6, f"Amdahl ceiling {1/f:.0f}x", fontsize=9, color=col)
        ax.set_xlim(0, 33); ax.set_ylim(0, min(36, 1/f + 6))
        ax.set_xticks([1,4,8,12,16,20,24,28,32])
        ax.yaxis.set_major_formatter(sfmt)
        ax.set_xlabel("Worker count"); ax.set_ylabel("Speedup over serial")
        ax.set_title(title + "  ($n=4\\times10^7$)")
        tidy(ax); ax.legend(loc="upper left", fontsize=9)
        save(fig, fname)
        print(f"    {name}: serial fraction f = {f:.4f} ({f*100:.2f}%), "
              f"ceiling {1/f:.1f}x  [fitted at p={p_fit}, S={s_fit:.2f}]")

# ---- REQUIRED GRAPH 4: hybrid vs Task 1 MPI, increasing threads per process,
#      with the MPI process count held equal between the two. ----
def g4_required():
    fig, ax = plt.subplots()
    mpi_t = {int(r["workers"]): float(r["mpi"]) for r in wk if fl(r["mpi"])}
    procs = [1, 2, 4, 8]
    cols  = [BLUE, ORANGE, AQUA, VIOLET]
    for P, c in zip(procs, cols):
        rows = sorted([r for r in hy if int(r["procs"]) == P],
                      key=lambda r: int(r["threads"]))
        xs = [int(r["threads"]) for r in rows]
        ys = [SERIAL_40M/float(r["seconds"]) for r in rows]
        ax.plot(xs, ys, "-o", color=c, lw=2, ms=5.5,
                label=f"Hybrid, {P} MPI process{'es' if P>1 else ''}")
        if P in mpi_t:
            ax.axhline(SERIAL_40M/mpi_t[P], color=c, ls="--", lw=1.3, alpha=.75)
            ax.text(8.3, SERIAL_40M/mpi_t[P], f"Task 1 MPI, {P} proc",
                    fontsize=8, color=c, va="center")
    ax.set_xscale("log", base=2); ax.set_xticks([1,2,4,8,16])
    ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v,p: f"{int(v)}"))
    ax.set_xlim(0.85, 13); ax.set_ylim(0, 18)
    ax.yaxis.set_major_formatter(sfmt)
    ax.set_xlabel("OpenMP threads per MPI process")
    ax.set_ylabel("Speedup over serial")
    ax.set_title("Hybrid vs pure MPI as threads increase  ($n=4\\times10^7$)")
    tidy(ax); ax.legend(loc="upper left", fontsize=8.5)
    save(fig, "caas_4_hybrid_vs_mpi_threads")

# ---- REQUIRED GRAPH 5: hybrid vs shared-memory implementations, where the
#      thread count of POSIX/OpenMP equals the hybrid's TOTAL worker count. ----
def g5_required():
    fig, ax = plt.subplots()
    best = {}
    for r in hy:
        w = int(r["workers"]); t = float(r["seconds"])
        if w not in best or t < best[w][0]: best[w] = (t, f"{r['procs']}x{r['threads']}")
    sm = {int(r["workers"]): r for r in wk}
    totals = [1, 2, 4, 8, 16, 32]

    for key in ("pthreads", "openmp"):
        st = STYLE[key]
        xs = [w for w in totals if w in sm and fl(sm[w][key])]
        ys = [SERIAL_40M/float(sm[w][key]) for w in xs]
        ax.plot(xs, ys, "-", color=st["color"], marker=st["marker"], lw=2, ms=6,
                label=f"{st['label']} ({'{'}n{'}'} threads)".replace("{n}", "matched"))
    xs = [w for w in totals if w in best]
    st = STYLE["hybrid"]
    ax.plot(xs, [SERIAL_40M/best[w][0] for w in xs], "-", color=st["color"],
            marker=st["marker"], lw=2, ms=6, label="Hybrid (best split)")
    for w in xs:
        ax.annotate(best[w][1], xy=(w, SERIAL_40M/best[w][0]),
                    xytext=(0, 9), textcoords="offset points", ha="center",
                    fontsize=7.5, color=VIOLET)
    ax.axvspan(16.8, 40, color=VIOLET, alpha=.05, zorder=0)
    ax.annotate("POSIX/OpenMP cannot reach 32 -\nthey are limited to one node's 16 cores",
                xy=(22, 4.5), fontsize=8.5, color=MUTED)
    ax.set_xscale("log", base=2); ax.set_xticks(totals)
    ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v,p: f"{int(v)}"))
    ax.set_xlim(0.85, 40); ax.set_ylim(0, 18)
    ax.yaxis.set_major_formatter(sfmt)
    ax.set_xlabel("Total workers  (hybrid processes x threads = thread count for POSIX/OpenMP)")
    ax.set_ylabel("Speedup over serial")
    ax.set_title("Hybrid vs shared-memory, matched total threads  ($n=4\\times10^7$)")
    tidy(ax); ax.legend(loc="upper left", fontsize=9)
    save(fig, "caas_5_hybrid_vs_shared_matched")


if __name__ == "__main__":
    print("Writing CAAS graphs:")
    g1(); g2(); g3()
    g4(); g4_required(); g5_required(); g67()
    print("Done.")
