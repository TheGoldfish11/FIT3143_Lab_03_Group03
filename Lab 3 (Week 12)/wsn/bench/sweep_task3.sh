#!/usr/bin/env bash
# FIT3143 Lab 3 - Task 3 communication delay sweep on a laptop
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# Runs every grid size (Task 3a) and line length (Task 3b) in bench/configs.sh, REPEATS times,
# appending one CSV row per run. Then plot with plot_task3.py.
#
# Usage (from the wsn/ directory, after make):
#   bench/sweep_task3.sh                       # both sweeps, about 35 minutes with 3 repeats
#   WHICH=lines REPEATS=1 bench/sweep_task3.sh # just the lines, once
#   MPIRUN="mpirun --allow-run-as-root --oversubscribe" bench/sweep_task3.sh

set -euo pipefail
source "$(dirname "$0")/configs.sh"

WHICH=${WHICH:-both}            # grids, lines or both
MPIRUN=${MPIRUN:-"mpirun --oversubscribe"}
OUTDIR=${OUTDIR:-results/task3}
mkdir -p "$OUTDIR/logs"

case "$WHICH" in
    grids) sets="grids" ;;
    lines) sets="lines" ;;
    *)     sets="grids lines" ;;
esac

for rep in $(seq 1 "$REPEATS"); do
    for set in $sets; do
        if [ "$set" = grids ]; then sizes=$GRIDS; else sizes=$LINES; fi
        for size in $sizes; do
            m=${size%x*}
            n=${size#*x}
            seed=$((2000 + rep))
            echo "[task3] repeat $rep/$REPEATS  $set  ${m}x${n}"
            $MPIRUN -np $((m * n + 1)) ./wsn -m "$m" -n "$n" -d "$DURATION" -c "$CYCLE_MS" \
                -a "$P_ARRIVE" -r "$P_DEPART" -i "$POLL_US" -s "$seed" -b "$BASE" -N "$NODE" \
                -o "$OUTDIR/logs/${set}-${m}x${n}-r${rep}.log" -C "$OUTDIR/${set}.csv" > /dev/null
        done
    done
done

echo "[task3] done, results in $OUTDIR/"
