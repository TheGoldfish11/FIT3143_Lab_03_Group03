#!/bin/bash
#SBATCH --job-name=fit3143-reps-mpi
#SBATCH --time=00:28:00
#SBATCH --partition=defq
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=16
#SBATCH --cpus-per-task=1
#SBATCH --exclusive
#SBATCH --output=reps_mpi-%j.out
#
# Repeats the distributed measurements (median of 3) across two nodes.

module load gcc/11.2.0 openmpi/4.1.5-gcc-11.2.0-ux65npg

t_of() { sed -n 's/.*time=\([0-9.]*\).*/\1/p' | tail -1; }
median3() { printf '%s\n' "$1" "$2" "$3" | sort -g | sed -n '2p'; }

echo "n,mpi16,hybrid16" > results_mpi_med.csv

for i in $(seq 0 29); do
  N=$(( 20000000 + i * 2000000 ))

  M1=$(srun --nodes=2 --ntasks=16 --cpus-per-task=1 ./task1_mpi $N | t_of)
  M2=$(srun --nodes=2 --ntasks=16 --cpus-per-task=1 ./task1_mpi $N | t_of)
  M3=$(srun --nodes=2 --ntasks=16 --cpus-per-task=1 ./task1_mpi $N | t_of)
  M=$(median3 "$M1" "$M2" "$M3")

  export OMP_NUM_THREADS=4
  H1=$(srun --nodes=2 --ntasks=4 --cpus-per-task=4 ./task2_hybrid $N | t_of)
  H2=$(srun --nodes=2 --ntasks=4 --cpus-per-task=4 ./task2_hybrid $N | t_of)
  H3=$(srun --nodes=2 --ntasks=4 --cpus-per-task=4 ./task2_hybrid $N | t_of)
  H=$(median3 "$H1" "$H2" "$H3")

  echo "$N,$M,$H" >> results_mpi_med.csv
  echo "  n=$N mpi=$M (of $M1 $M2 $M3) hybrid=$H (of $H1 $H2 $H3)" >&2
done

echo "=== results_mpi_med.csv ==="; cat results_mpi_med.csv
