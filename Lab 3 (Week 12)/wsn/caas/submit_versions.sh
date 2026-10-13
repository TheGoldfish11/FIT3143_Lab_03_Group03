#!/usr/bin/env bash
# FIT3143 Lab 3 - queue the blocking vs non-blocking version benchmark on CAAS
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# One job per base station / node version combination (6 jobs), each running REPEATS times.
#   caas/submit_versions.sh
#   python3 bench/plot_versions.py results/caas/versions     # when the jobs are done

set -euo pipefail
source bench/configs.sh
source caas/common.sh

GRID_M=${GRID_M:-4}
GRID_N=${GRID_N:-4}
VER_DURATION=${VER_DURATION:-15}
VER_REPEATS=${VER_REPEATS:-5}
VER_POLL_US=${VER_POLL_US:-1000}   # the default poll interval, as in the laptop benchmark
OUTDIR=results/caas/versions

for base in poll block irecv; do
    for node in nonblock block; do
        submit "ver-${base}-${node}" $((GRID_M * GRID_N + 1)) \
            "-m $GRID_M -n $GRID_N -d $VER_DURATION -c $CYCLE_MS -a $P_ARRIVE -r $P_DEPART -i $VER_POLL_US -b $base -N $node" \
            "$VER_REPEATS" 1000 "$OUTDIR/${base}-${node}.csv" "$OUTDIR/logs/${base}-${node}"
    done
done
