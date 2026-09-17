#!/bin/bash
#SBATCH --job-name=fit3143-fixup
#SBATCH --time=00:28:00
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --output=fixup-%j.out
# Re-runs only the serial / pthreads / OpenMP measurements that the earlier
# sweeps failed to parse. All three live on one node by nature (shared memory).

module load gcc/11.2.0 openmpi/4.1.5-gcc-11.2.0-ux65npg

# handles all three output formats:
#   "Time taken: 2.05 seconds"  /  "Parallel computation time: 0.17 seconds"
t_of() { sed -n 's/.*[Tt]ime[^0-9]*\([0-9][0-9.]*\).*/\1/p' | tail -1; }

echo "n,impl,workers,seconds" > results_shared.csv

echo "### part 1: n sweep at 16 workers (30 values)" >&2
for i in $(seq 0 29); do
  N=$(( 20000000 + i * 2000000 ))
  T=$(echo $N | ./lab1_serial | t_of);                          echo "$N,serial,1,$T"      >> results_shared.csv
  T=$(printf "$N\n16\n" | ./lab1_pthread | t_of);               echo "$N,pthreads,16,$T"   >> results_shared.csv
  T=$(echo $N | OMP_NUM_THREADS=16 ./lab1_openmp | t_of);       echo "$N,openmp,16,$T"     >> results_shared.csv
  echo "  n=$N serial=$T" >&2
done

echo "### part 2: worker sweep at n=4e7" >&2
echo "n,impl,workers,seconds" > results_shared_workers.csv
N=40000000
T=$(echo $N | ./lab1_serial | t_of); echo "$N,serial,1,$T" >> results_shared_workers.csv
for W in 1 2 4 6 8 10 12 14 16; do
  T=$(printf "$N\n$W\n" | ./lab1_pthread | t_of);           echo "$N,pthreads,$W,$T" >> results_shared_workers.csv
  T=$(echo $N | OMP_NUM_THREADS=$W ./lab1_openmp | t_of);   echo "$N,openmp,$W,$T"   >> results_shared_workers.csv
  echo "  w=$W done" >&2
done

echo "=== results_shared.csv ==="; cat results_shared.csv
echo "=== results_shared_workers.csv ==="; cat results_shared_workers.csv
