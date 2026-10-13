#!/bin/bash
# FIT3143 Lab 3 - one CAAS job: runs the simulation REPEATS times with the same settings
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# Not submitted by hand: the caas/submit_*.sh scripts set --ntasks (m*n + 1) and these
# environment variables, which sbatch passes into the job:
#   RUN_ARGS    wsn options except -s, -o and -C
#   REPEATS     runs in this job
#   SEED0       seed of the first run minus 1
#   OUT_CSV     CSV file each run appends its summary row to
#   LOG_PREFIX  base station log path prefix (one log per run)
#
#SBATCH --job-name=wsn
#SBATCH --time=00:10:00          ### CAAS limit: 10 minutes per job
#SBATCH --mem=16G
#SBATCH --cpus-per-task=1        ### port threads mostly sleep, so they share their process's core
#SBATCH --partition=defq
#SBATCH --output=results/caas/slurm/%x-%j.out

module load openmpi/4.1.5-gcc-11.2.0-ux65npg

echo "job $SLURM_JOB_ID: $SLURM_NTASKS tasks on $SLURM_JOB_NUM_NODES node(s): $SLURM_JOB_NODELIST"
for rep in $(seq 1 "$REPEATS"); do
    srun ./wsn $RUN_ARGS -s $((SEED0 + rep)) -o "${LOG_PREFIX}-r${rep}.log" -C "$OUT_CSV"
done
