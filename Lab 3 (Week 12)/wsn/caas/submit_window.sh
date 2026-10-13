#!/usr/bin/env bash
# FIT3143 Lab 3 - queue the window (-w) test on CAAS: one job per window value
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#   caas/submit_window.sh
#   python3 bench/plot_window.py results/caas/window          # when the jobs are done

set -euo pipefail
source bench/configs.sh
source caas/common.sh

GRID_M=${GRID_M:-4}
GRID_N=${GRID_N:-4}
WIN_DURATION=${WIN_DURATION:-20}
OUTDIR=results/caas/window

for w in $WINDOWS; do
    submit "win-${w}" $((GRID_M * GRID_N + 1)) \
        "-m $GRID_M -n $GRID_N -d $WIN_DURATION -c $CYCLE_MS -a $P_ARRIVE -r $P_DEPART -i $POLL_US -w $w -b $BASE -N $NODE" \
        "$REPEATS" 3000 "$OUTDIR/w${w}.csv" "$OUTDIR/logs/w${w}"
done
