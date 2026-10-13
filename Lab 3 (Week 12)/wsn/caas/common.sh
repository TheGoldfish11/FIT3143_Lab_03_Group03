# FIT3143 Lab 3 - helper for the CAAS submit scripts (sourced, not run)
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)

# processes per machine; CAAS machines have 16 cores. Use fewer (e.g. 4) to spread a job over
# more machines, so more messages cross the Gigabit network.
TASKS_PER_NODE=${TASKS_PER_NODE:-16}
DRY_RUN=${DRY_RUN:-0}           # 1 = print the sbatch commands instead of submitting

mkdir -p results/caas/slurm

# submit NAME NTASKS RUN_ARGS REPEATS SEED0 OUT_CSV LOG_PREFIX
submit() {
    local name=$1 np=$2 args=$3 repeats=$4 seed0=$5 csv=$6 prefix=$7
    local tpn=$TASKS_PER_NODE
    if [ "$np" -lt "$tpn" ]; then tpn=$np; fi
    mkdir -p "$(dirname "$csv")" "$(dirname "$prefix")"
    if [ "$DRY_RUN" = 1 ]; then
        echo "RUN_ARGS=\"$args\" REPEATS=$repeats SEED0=$seed0 OUT_CSV=$csv LOG_PREFIX=$prefix" \
             "sbatch --job-name=$name --ntasks=$np --ntasks-per-node=$tpn caas/wsn_job.slurm"
    else
        RUN_ARGS="$args" REPEATS=$repeats SEED0=$seed0 OUT_CSV=$csv LOG_PREFIX=$prefix \
            sbatch --job-name="$name" --ntasks="$np" --ntasks-per-node="$tpn" caas/wsn_job.slurm
    fi
}
