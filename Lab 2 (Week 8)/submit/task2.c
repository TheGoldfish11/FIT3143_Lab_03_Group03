/*
 * FIT3143 Lab 2 - Task 2
 * Hybrid prime search: Open MPI (distributed memory) + OpenMP (shared memory).
 *
 * BUILD   OMPI_CC=gcc-16 mpicc -O2 -fopenmp -o task2 task2.c -lm
 * RUN     OMP_NUM_THREADS=4 mpirun -np 2 ./task2 10000000
 *
 * TWO LEVELS OF PARALLELISM
 *   Level 1 (MPI)    - the range [0, n) is cut into chunks and dealt out to the
 *                      MPI processes round-robin, exactly as in Task 1.
 *   Level 2 (OpenMP) - within a process, its own chunks are handed to threads
 *                      dynamically, so a thread that finishes early takes
 *                      another chunk instead of idling.
 *
 * Threads collect into their own private lists, so no locking is needed in the
 * search loop. The lists are concatenated once the parallel region ends.
 */

#include <mpi.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define CHUNKS_PER_WORKER 8    /* chunks per thread, per process */

int is_prime(long k) {
    if (k < 2)      return 0;
    if (k == 2)     return 1;
    if (k % 2 == 0) return 0;
    long limit = (long)sqrt((double)k);
    for (long i = 3; i <= limit; i += 2) {
        if (k % i == 0) return 0;
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

/* one growable list per thread, so threads never contend while searching */
typedef struct {
    long *values;
    long  count;
    long  capacity;
} PrimeList;

int main(int argc, char **argv) {
    int provided;
    /* MPI_THREAD_FUNNELED: only the main thread of each process calls MPI */
    MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (argc < 2) {
        if (rank == 0) fprintf(stderr, "Usage: %s <n>\n", argv[0]);
        MPI_Finalize();
        return 1;
    }
    if (rank == 0 && provided < MPI_THREAD_FUNNELED) {
        fprintf(stderr, "Warning: MPI library lacks MPI_THREAD_FUNNELED support\n");
    }

    long n = 0;
    if (rank == 0) n = atol(argv[1]);
    MPI_Bcast(&n, 1, MPI_LONG, 0, MPI_COMM_WORLD);

    /* every process must agree on the chunk count, so rank 0 decides it */
    int threads = omp_get_max_threads();
    MPI_Bcast(&threads, 1, MPI_INT, 0, MPI_COMM_WORLD);
    omp_set_num_threads(threads);

    long num_chunks = (long)size * threads * CHUNKS_PER_WORKER;
    long chunk_size = (n + num_chunks - 1) / num_chunks;   /* ceiling division */

    MPI_Barrier(MPI_COMM_WORLD);
    double t_start = MPI_Wtime();
    double t_search_start = MPI_Wtime();
    
    /* --- how many chunks belong to this process? --- */
    long my_chunks = 0;
    for (long c = rank; c < num_chunks; c += size) my_chunks++;

    PrimeList *lists = malloc(threads * sizeof(PrimeList));
    for (int t = 0; t < threads; t++) {
        lists[t].capacity = 1024;
        lists[t].count = 0;
        lists[t].values = malloc(lists[t].capacity * sizeof(long));
    }

    /* --- level 2: threads take this process's chunks on demand --- */
    #pragma omp parallel
    {
        int tid = omp_get_thread_num();
        PrimeList *mine = &lists[tid];

        #pragma omp for schedule(dynamic, 1)
        for (long i = 0; i < my_chunks; i++) {
            long chunk = rank + i * size;          /* level 1: this rank's chunk */
            long first = chunk * chunk_size;
            long last  = first + chunk_size;
            if (last > n)  last = n;
            if (first < 2) first = 2;

            for (long num = first; num < last; num++) {
                if (is_prime(num)) {
                    if (mine->count == mine->capacity) {
                        mine->capacity *= 2;
                        mine->values = realloc(mine->values,
                                               mine->capacity * sizeof(long));
                    }
                    mine->values[mine->count++] = num;
                }
            }
        }
    }

    double t_search_end = MPI_Wtime();
    double local_search_time = t_search_end - t_search_start;
    double max_search_time = 0.0;

    MPI_Reduce(&local_search_time, &max_search_time, 1,
               MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    /* --- concatenate this process's thread lists --- */
    long local_count = 0;
    for (int t = 0; t < threads; t++) local_count += lists[t].count;
    long *local_primes = malloc(local_count * sizeof(long));
    long at = 0;
    for (int t = 0; t < threads; t++) {
        for (long j = 0; j < lists[t].count; j++) local_primes[at++] = lists[t].values[j];
        free(lists[t].values);
    }
    free(lists);

    /* --- gather every process's primes onto the root --- */
    int  local_count_int = (int)local_count;
    int *counts = NULL, *displs = NULL;
    long *all_primes = NULL;
    int total_count = 0;

    double t_comm_start = MPI_Wtime();

    if (rank == 0) counts = malloc(size * sizeof(int));
    MPI_Gather(&local_count_int, 1, MPI_INT, counts, 1, MPI_INT, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        displs = malloc(size * sizeof(int));
        displs[0] = 0;
        for (int i = 1; i < size; i++) displs[i] = displs[i-1] + counts[i-1];
        total_count = displs[size-1] + counts[size-1];
        all_primes = malloc(total_count * sizeof(long));
    }
    MPI_Gatherv(local_primes, local_count_int, MPI_LONG,
                all_primes, counts, displs, MPI_LONG, 0, MPI_COMM_WORLD);

    double t_comm_end = MPI_Wtime();
    double local_comm_time = t_comm_end - t_comm_start;
    double max_comm_time = 0.0;

    MPI_Reduce(&local_comm_time, &max_comm_time, 1,
               MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    /* --- root sorts and writes; chunks were interleaved so order is scrambled --- */
    if (rank == 0) {
        double t_post_start = MPI_Wtime();

        qsort(all_primes, total_count, sizeof(long), compare_long);

        FILE *fp = fopen("primes_output.txt", "w");
        if (fp == NULL) {
            fprintf(stderr, "Error: could not open output file\n");
        } else {
            for (int i = 0; i < total_count; i++) fprintf(fp, "%ld\n", all_primes[i]);
            fclose(fp);
        }

        double t_post_end = MPI_Wtime();
        double post_time = t_post_end - t_post_start;

        double t_end = MPI_Wtime();
        printf("n=%ld, processes=%d, threads=%d, total workers=%d, "
            "primes found=%d, total=%f seconds, search=%f seconds, "
            "communication=%f seconds, post=%f seconds\n",
            n, size, threads, size * threads, total_count,
            t_end - t_start,
            max_search_time,
            max_comm_time,
            post_time);
            
        free(all_primes); free(counts); free(displs);
    }

    free(local_primes);
    MPI_Finalize();
    return 0;
}
