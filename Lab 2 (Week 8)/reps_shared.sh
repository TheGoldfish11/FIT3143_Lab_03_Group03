#!/bin/bash
#SBATCH --job-name=fit3143-reps-shared
#SBATCH --time=00:28:00
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --exclusive
#SBATCH --output=reps_shared-%j.out
#
# Repeats the shared-memory measurements and reports the MEDIAN of 3 runs.
#
# Why 3 reps for the threaded runs but 1 for serial: the serial program uses a
# single core on an otherwise idle node, so it is very stable. The 16-thread
# runs use every core and are the ones vulnerable to interference - which is
# what produced the OpenMP spike at n=72,000,000 in the single-run data.
# --exclusive stops any other job sharing this node.

module load gcc/11.2.0 openmpi/4.1.5-gcc-11.2.0-ux65npg

t_of() { sed -n 's/.*[Tt]ime[^0-9]*\([0-9][0-9.]*\).*/\1/p' | tail -1; }
median3() { printf '%s\n' "$1" "$2" "$3" | sort -g | sed -n '2p'; }

echo "n,serial,pthreads16,openmp16" > results_shared_med.csv

for i in $(seq 0 29); do
  N=$(( 20000000 + i * 2000000 ))

  S=$(echo $N | ./lab1_serial | t_of)

  P1=$(printf "$N\n16\n" | ./lab1_pthread | t_of)
  P2=$(printf "$N\n16\n" | ./lab1_pthread | t_of)
  P3=$(printf "$N\n16\n" | ./lab1_pthread | t_of)
  P=$(median3 "$P1" "$P2" "$P3")

  O1=$(echo $N | OMP_NUM_THREADS=16 ./lab1_openmp | t_of)
  O2=$(echo $N | OMP_NUM_THREADS=16 ./lab1_openmp | t_of)
  O3=$(echo $N | OMP_NUM_THREADS=16 ./lab1_openmp | t_of)
  O=$(median3 "$O1" "$O2" "$O3")

  echo "$N,$S,$P,$O" >> results_shared_med.csv
  echo "  n=$N serial=$S pthreads=$P (of $P1 $P2 $P3) openmp=$O (of $O1 $O2 $O3)" >&2
done

echo "=== results_shared_med.csv ==="; cat results_shared_med.csv
