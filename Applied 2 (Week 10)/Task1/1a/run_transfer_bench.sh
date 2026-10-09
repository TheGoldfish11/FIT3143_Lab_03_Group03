#!/bin/bash
# FIT3143 Applied 2 - Task 1a: run transfer_bench on a CAAS GPU node.
#
# Before the first run, check the names used on CAAS and edit below if needed:
#   module avail cuda        -> name of the CUDA module
#   sinfo -o "%P %G"         -> partition name and GPU resource (gres) name
#
# Submit: sbatch run_transfer_bench.sh      Output: transfer_bench_<jobid>.out

#SBATCH --job-name=transfer_bench
#SBATCH --partition=defq
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=transfer_bench_%j.out

module load cuda 2>/dev/null || echo "WARNING: 'module load cuda' failed - check 'module avail cuda'"

nvidia-smi --query-gpu=name,memory.total,pcie.link.gen.current,pcie.link.width.current --format=csv
nvcc -O2 -o transfer_bench transfer_bench.cu || exit 1

# 1080p, 4K and 8K images: shows the transfer time growing with image size
for size in "1920 1080" "3840 2160" "7680 4320"; do
    echo "=================== $size ==================="
    ./transfer_bench $size 12 3
done
