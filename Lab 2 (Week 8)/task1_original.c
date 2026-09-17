#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define CHUNKS_PER_PROCESS 8   // tune this and re-test for Task 3

int is_prime(long k) {
    if (k < 2) {
        return 0;
    }
    if (k == 2) {
        return 1;
    }
    if (k % 2 == 0) {
        return 0;
    }
    long limit = (long)sqrt((double)k);
    for (long i = 3; i <= limit; i += 2) {
        if (k % i == 0) {
            return 0;
        }
    }
    return 1;
}

int compare_long(const void *a, const void *b) {
    long la = *(const long *)a;
    long lb = *(const long *)b;
    if (la < lb) return -1;
    if (la > lb) return 1;
    return 0;
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (argc < 2) { // in case the user forgets to provide n, print usage message and exit
        if (rank == 0) {
            fprintf(stderr, "Usage: %s <n>\n", argv[0]);
        }
        MPI_Finalize();
        return 1;
    }

    long n = 0;
    if (rank == 0) {
        n = atol(argv[1]); // set n to the value provided by the user on the command line
    }
    MPI_Bcast(&n, 1, MPI_LONG, 0, MPI_COMM_WORLD); // if process is rank 0 it will broadcast the value of n to all other processes

    // all processes wait here so the timer starts at the same moment for everyone
    MPI_Barrier(MPI_COMM_WORLD);
    double t_start = MPI_Wtime();   // useful for Task 3 timing

    // --- chunked round-robin workload distribution ---
    int num_chunks = size * CHUNKS_PER_PROCESS;
    long chunk_size = (n + num_chunks - 1) / num_chunks;  // ceiling division

    long local_capacity = 1024;
    long local_count = 0;
    long *local_primes = malloc(local_capacity * sizeof(long));

    for (int chunk = rank; chunk < num_chunks; chunk += size) {
        long start = chunk * chunk_size;
        long end = start + chunk_size;
        if (end > n) end = n;
        if (start < 2) start = 2;

        for (long num = start; num < end; num++) {
            if (is_prime(num)) {
                if (local_count == local_capacity) {
                    local_capacity *= 2;
                    local_primes = realloc(local_primes, local_capacity * sizeof(long));
                }
                local_primes[local_count++] = num;
            }
        }
    }

    // --- gather variable-length results to root ---
    int local_count_int = (int)local_count;
    int *counts = NULL;
    int *displs = NULL;
    long *all_primes = NULL;
    int total_count = 0;

    if (rank == 0) {
        counts = malloc(size * sizeof(int));
    }
    MPI_Gather(&local_count_int, 1, MPI_INT, counts, 1, MPI_INT, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        displs = malloc(size * sizeof(int));
        displs[0] = 0;
        for (int i = 1; i < size; i++) {
            displs[i] = displs[i - 1] + counts[i - 1];
        }
        total_count = displs[size - 1] + counts[size - 1];
        all_primes = malloc(total_count * sizeof(long));
    }

    MPI_Gatherv(local_primes, local_count_int, MPI_LONG,
                all_primes, counts, displs, MPI_LONG, 0, MPI_COMM_WORLD);

    // --- root sorts (chunked interleaving means gathered order isn't sorted) and writes output ---
    if (rank == 0) {
        qsort(all_primes, total_count, sizeof(long), compare_long);

        FILE *fp = fopen("primes_output.txt", "w");
        if (fp == NULL) {
            fprintf(stderr, "Error: could not open output file\n");
        } else {
            for (int i = 0; i < total_count; i++) {
                fprintf(fp, "%ld\n", all_primes[i]);
            }
            fclose(fp);
        }

        // timer stops here so the sort and the file write are included
        double t_end = MPI_Wtime();

        printf("n=%ld, processes=%d, primes found=%d, time=%f seconds\n",
               n, size, total_count, t_end - t_start);

        free(all_primes);
        free(counts);
        free(displs);
    }

    free(local_primes);
    MPI_Finalize();
    return 0;
}