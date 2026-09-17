#!/bin/bash

OUTPUT="pilot_results.csv"

echo "task,n,processes,threads,total_workers,total,search,communication,post" > "$OUTPUT"

N_VALUES=(1000000 2000000 5000000 10000000 20000000 30000000 50000000)

echo "Running Task 1 pilot..."

for n in "${N_VALUES[@]}"; do
    for p in 1 2 4 8 16; do

        echo "Task 1: n=$n, processes=$p"

        result=$(mpirun -np "$p" --bind-to none ./task1 "$n")

        echo "$result"

        # Convert:
        # n=10000000, processes=4, primes found=..., total=..., search=..., communication=..., post=...
        # into CSV fields.
        n_value=$(echo "$result" | cut -d',' -f1 | cut -d'=' -f2)
        p_value=$(echo "$result" | cut -d',' -f2 | cut -d'=' -f2)
        total=$(echo "$result" | cut -d',' -f4 | cut -d'=' -f2 | cut -d' ' -f1)
        search=$(echo "$result" | cut -d',' -f5 | cut -d'=' -f2 | cut -d' ' -f1)
        communication=$(echo "$result" | cut -d',' -f6 | cut -d'=' -f2 | cut -d' ' -f1)
        post=$(echo "$result" | cut -d',' -f7 | cut -d'=' -f2 | cut -d' ' -f1)

        echo "task1,$n_value,$p_value,1,$p_value,$total,$search,$communication,$post" >> "$OUTPUT"

    done
done


echo "Running Task 2 pilot..."

for n in "${N_VALUES[@]}"; do

    for config in "1 1" "1 4" "1 8" "2 4" "4 2" "8 1"; do

        set -- $config
        p=$1
        threads=$2

        echo "Task 2: n=$n, processes=$p, threads=$threads"

        result=$(OMP_NUM_THREADS="$threads" \
                 mpirun -np "$p" --bind-to none ./task2 "$n")

        echo "$result"

        n_value=$(echo "$result" | cut -d',' -f1 | cut -d'=' -f2)
        p_value=$(echo "$result" | cut -d',' -f2 | cut -d'=' -f2)
        threads_value=$(echo "$result" | cut -d',' -f3 | cut -d'=' -f2)
        workers=$(echo "$result" | cut -d',' -f4 | cut -d'=' -f2)
        total=$(echo "$result" | cut -d',' -f6 | cut -d'=' -f2 | cut -d' ' -f1)
        search=$(echo "$result" | cut -d',' -f7 | cut -d'=' -f2 | cut -d' ' -f1)
        communication=$(echo "$result" | cut -d',' -f8 | cut -d'=' -f2 | cut -d' ' -f1)
        post=$(echo "$result" | cut -d',' -f9 | cut -d'=' -f2 | cut -d' ' -f1)

        echo "task2,$n_value,$p_value,$threads_value,$workers,$total,$search,$communication,$post" >> "$OUTPUT"

    done
done

echo
echo "======================================"
echo "Pilot complete!"
echo "Results saved to: $OUTPUT"
echo "======================================"