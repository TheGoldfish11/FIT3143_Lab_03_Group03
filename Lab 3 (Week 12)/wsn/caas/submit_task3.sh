#!/usr/bin/env bash
# FIT3143 Lab 3 - queue the Task 3 sweep on CAAS: one job per grid size and line length
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# Run on the CAAS head node from the wsn/ directory, after building:
#   module load openmpi/4.1.5-gcc-11.2.0-ux65npg && make
#   caas/submit_task3.sh                  # 60 jobs; CAAS runs one at a time, ~40 s each
#   DRY_RUN=1 caas/submit_task3.sh        # show the commands only
# When all jobs are done (squeue -u $USER is empty):
#   python3 bench/plot_task3.py results/caas/task3

set -euo pipefail
source bench/configs.sh
source caas/common.sh

OUTDIR=results/caas/task3
WHICH=${WHICH:-both}

for set in grids lines; do
    if [ "$WHICH" != both ] && [ "$WHICH" != "$set" ]; then continue; fi
    if [ "$set" = grids ]; then sizes=$GRIDS; else sizes=$LINES; fi
    for size in $sizes; do
        m=${size%x*}
        n=${size#*x}
        submit "t3-${m}x${n}" $((m * n + 1)) \
            "-m $m -n $n -d $DURATION -c $CYCLE_MS -a $P_ARRIVE -r $P_DEPART -i $POLL_US -b $BASE -N $NODE" \
            "$REPEATS" 2000 "$OUTDIR/${set}-${m}x${n}.csv" "$OUTDIR/logs/${set}-${m}x${n}"
    done
done
