#!/usr/bin/env bash
# FIT3143 Lab 3 - benchmark the base station and node versions against each other
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# Runs every combination of base station version (poll, block, irecv) and node version
# (nonblock, block) on the same grid and settings, REPEATS times each, and appends one CSV row
# per run. Repeats are interleaved (all six versions, then all six again) so a slow patch on
# the machine does not land on one version only. Then plot with plot_versions.py.
#
# Usage (from the wsn/ directory, after make):
#   bench/bench_versions.sh
#   GRID_M=5 GRID_N=5 REPEATS=5 bench/bench_versions.sh
#   MPIRUN="mpirun --allow-run-as-root --oversubscribe" bench/bench_versions.sh

set -euo pipefail

GRID_M=${GRID_M:-4}
GRID_N=${GRID_N:-4}
DURATION=${DURATION:-15}        # seconds per run
REPEATS=${REPEATS:-3}
CYCLE_MS=${CYCLE_MS:-500}
P_ARRIVE=${P_ARRIVE:-0.8}       # busy grid, so there are plenty of reports to time
P_DEPART=${P_DEPART:-0.2}
MPIRUN=${MPIRUN:-"mpirun --oversubscribe"}
OUT=${OUT:-results/versions.csv}
LOGS=$(dirname "$OUT")/logs

NP=$((GRID_M * GRID_N + 1))
mkdir -p "$LOGS"

for rep in $(seq 1 "$REPEATS"); do
    for base in poll block irecv; do
        for node in nonblock block; do
            seed=$((1000 + rep))
            echo "[bench] repeat $rep/$REPEATS  base=$base  nodes=$node  (${GRID_M}x${GRID_N}, ${DURATION}s)"
            $MPIRUN -np "$NP" ./wsn -m "$GRID_M" -n "$GRID_N" -d "$DURATION" -c "$CYCLE_MS" \
                -a "$P_ARRIVE" -r "$P_DEPART" -s "$seed" -b "$base" -N "$node" \
                -o "$LOGS/${base}-${node}-r${rep}.log" -C "$OUT" > /dev/null
        done
    done
done

echo "[bench] done: $((REPEATS * 6)) runs appended to $OUT"
