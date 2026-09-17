#!/bin/bash

# ============================================================
# FIT3143 Task 3 - Final Benchmark
#
# Collects:
#   1. Serial baseline
#   2. Task 1 MPI scaling
#   3. Task 2 hybrid MPI + OpenMP scaling
#
# The script is RESUME-SAFE:
#   - Each successful run is written immediately to the CSV.
#   - If restarted, completed runs are skipped.
#
# Each configuration is run 3 times.
# ============================================================

OUTPUT="final_results.csv"
REPETITIONS=3

# ------------------------------------------------------------
# Problem sizes
# ------------------------------------------------------------

# 31 values for problem-size analysis
ALL_N_VALUES=(
    5000000
)

# Representative sizes for detailed parallel scaling
SCALING_N_VALUES=(
    5000000
)

# ------------------------------------------------------------
# CSV header
# ------------------------------------------------------------

if [ ! -f "$OUTPUT" ]; then
    echo "task,n,processes,threads,total_workers,run,total,search,communication,post" > "$OUTPUT"
fi


# ============================================================
# Helper function: check whether a run already exists
# ============================================================

run_exists() {
    local task=$1
    local n=$2
    local processes=$3
    local threads=$4
    local run=$5

    grep -q "^${task},${n},${processes},${threads},$((processes * threads)),${run}," "$OUTPUT"
}


# ============================================================
# Helper function: add a result to CSV
# ============================================================

save_task1_result() {
    local result="$1"
    local run="$2"

    n_value=$(echo "$result" | cut -d',' -f1 | cut -d'=' -f2)
    p_value=$(echo "$result" | cut -d',' -f2 | cut -d'=' -f2)

    total=$(echo "$result" | cut -d',' -f4 | cut -d'=' -f2 | cut -d' ' -f1)
    search=$(echo "$result" | cut -d',' -f5 | cut -d'=' -f2 | cut -d' ' -f1)
    communication=$(echo "$result" | cut -d',' -f6 | cut -d'=' -f2 | cut -d' ' -f1)
    post=$(echo "$result" | cut -d',' -f7 | cut -d'=' -f2 | cut -d' ' -f1)

    echo "task1,$n_value,$p_value,1,$p_value,$run,$total,$search,$communication,$post" >> "$OUTPUT"
}


save_task2_result() {
    local result="$1"
    local run="$2"

    n_value=$(echo "$result" | cut -d',' -f1 | cut -d'=' -f2)
    p_value=$(echo "$result" | cut -d',' -f2 | cut -d'=' -f2)
    threads_value=$(echo "$result" | cut -d',' -f3 | cut -d'=' -f2)
    workers=$(echo "$result" | cut -d',' -f4 | cut -d'=' -f2)

    total=$(echo "$result" | cut -d',' -f6 | cut -d'=' -f2 | cut -d' ' -f1)
    search=$(echo "$result" | cut -d',' -f7 | cut -d'=' -f2 | cut -d' ' -f1)
    communication=$(echo "$result" | cut -d',' -f8 | cut -d'=' -f2 | cut -d' ' -f1)
    post=$(echo "$result" | cut -d',' -f9 | cut -d'=' -f2 | cut -d' ' -f1)

    echo "task2,$n_value,$p_value,$threads_value,$workers,$run,$total,$search,$communication,$post" >> "$OUTPUT"
}


# ============================================================
# SERIAL BASELINE
# ============================================================

echo
echo "============================================================"
echo "SERIAL BASELINE"
echo "============================================================"

for n in "${ALL_N_VALUES[@]}"; do

    for run in $(seq 1 "$REPETITIONS"); do

        if run_exists "serial" "$n" 1 1 "$run"; then
            echo "SKIP serial: n=$n run=$run"
            continue
        fi

        echo
        echo "Serial: n=$n run=$run/$REPETITIONS"

        # Feed n into the interactive serial program.
        result=$(printf "%s\n" "$n" | ./serial)

        echo "$result"

        # Extract the timing.
        total=$(echo "$result" | grep "Time taken:" | awk '{print $3}')

        if [ -z "$total" ]; then
            echo "ERROR: Could not read serial timing."
            echo "Stopping benchmark."
            exit 1
        fi

        echo "serial,$n,1,1,1,$run,$total,$total,0,0" >> "$OUTPUT"

    done
done


# ============================================================
# TASK 1 - MPI PROCESS SCALING
# ============================================================

echo
echo "============================================================"
echo "TASK 1 - MPI PROCESS SCALING"
echo "============================================================"

PROCESS_COUNTS=(1 2 4 8 16)

for n in "${SCALING_N_VALUES[@]}"; do

    for p in "${PROCESS_COUNTS[@]}"; do

        for run in $(seq 1 "$REPETITIONS"); do

            if run_exists "task1" "$n" "$p" 1 "$run"; then
                echo "SKIP task1: n=$n processes=$p run=$run"
                continue
            fi

            echo
            echo "Task 1: n=$n processes=$p run=$run/$REPETITIONS"

            result=$(mpirun -np "$p" --bind-to none ./task1 "$n")

            echo "$result"

            if ! echo "$result" | grep -q "primes found="; then
                echo "ERROR: Task 1 did not produce valid output."
                echo "Stopping benchmark."
                exit 1
            fi

            save_task1_result "$result" "$run"

        done
    done
done


# ============================================================
# TASK 2 - HYBRID MPI + OPENMP SCALING
# ============================================================

echo
echo "============================================================"
echo "TASK 2 - HYBRID MPI + OPENMP SCALING"
echo "============================================================"

# MPI processes x OpenMP threads.
#
# Maximum total workers = 16, matching the available CPUs.
#
# 1x1   = 1 worker
# 1x2   = 2
# 1x4   = 4
# 1x8   = 8
# 1x16  = 16
# 2x1   = 2
# 2x2   = 4
# 2x4   = 8
# 2x8   = 16
# 4x1   = 4
# 4x2   = 8
# 4x4   = 16
# 8x1   = 8
# 8x2   = 16
# 16x1  = 16

CONFIGS=(
    "1 1"
    "1 2"
    "1 4"
    "1 8"
    "1 16"
    "2 1"
    "2 2"
    "2 4"
    "2 8"
    "4 1"
    "4 2"
    "4 4"
    "8 1"
    "8 2"
    "16 1"
)

for n in "${SCALING_N_VALUES[@]}"; do

    for config in "${CONFIGS[@]}"; do

        set -- $config
        p=$1
        threads=$2

        for run in $(seq 1 "$REPETITIONS"); do

            if run_exists "task2" "$n" "$p" "$threads" "$run"; then
                echo "SKIP task2: n=$n ${p}x${threads} run=$run"
                continue
            fi

            echo
            echo "Task 2: n=$n processes=$p threads=$threads run=$run/$REPETITIONS"

            result=$(OMP_NUM_THREADS="$threads" \
                     mpirun -np "$p" --bind-to none ./task2 "$n")

            echo "$result"

            if ! echo "$result" | grep -q "primes found="; then
                echo "ERROR: Task 2 did not produce valid output."
                echo "Stopping benchmark."
                exit 1
            fi

            save_task2_result "$result" "$run"

        done
    done
done


# ============================================================
# FINISHED
# ============================================================

echo
echo "============================================================"
echo "BENCHMARK COMPLETE"
echo "============================================================"
echo "Results saved to: $OUTPUT"
echo

echo "Number of CSV rows:"
wc -l "$OUTPUT"

echo
echo "You can inspect the results with:"
echo "  head $OUTPUT"
echo "  tail $OUTPUT"
echo "============================================================"