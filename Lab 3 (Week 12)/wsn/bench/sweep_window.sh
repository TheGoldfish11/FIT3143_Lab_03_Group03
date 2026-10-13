#!/usr/bin/env bash
# FIT3143 Lab 3 - test different base station window values (-w), as the spec asks
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# Same grid and settings for every window value, REPEATS times each. Then plot with
# plot_window.py.
#
# Usage (from the wsn/ directory, after make):
#   bench/sweep_window.sh                      # 4x4 grid, 20 s runs, about 10 minutes
#   GRID_M=5 GRID_N=5 bench/sweep_window.sh

set -euo pipefail
source "$(dirname "$0")/configs.sh"

GRID_M=${GRID_M:-4}
GRID_N=${GRID_N:-4}
WIN_DURATION=${WIN_DURATION:-20}   # longer than the biggest window, so the window can matter
MPIRUN=${MPIRUN:-"mpirun --oversubscribe"}
OUTDIR=${OUTDIR:-results/window}
mkdir -p "$OUTDIR/logs"

for rep in $(seq 1 "$REPEATS"); do
    for w in $WINDOWS; do
        seed=$((3000 + rep))
        echo "[window] repeat $rep/$REPEATS  w=${w}s  (${GRID_M}x${GRID_N})"
        $MPIRUN -np $((GRID_M * GRID_N + 1)) ./wsn -m "$GRID_M" -n "$GRID_N" -d "$WIN_DURATION" \
            -c "$CYCLE_MS" -a "$P_ARRIVE" -r "$P_DEPART" -i "$POLL_US" -w "$w" -s "$seed" \
            -b "$BASE" -N "$NODE" -o "$OUTDIR/logs/w${w}-r${rep}.log" -C "$OUTDIR/window.csv" > /dev/null
    done
done

echo "[window] done, results in $OUTDIR/"
