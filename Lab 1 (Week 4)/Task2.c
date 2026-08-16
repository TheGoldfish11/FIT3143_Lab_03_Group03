#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <pthread.h>

/*
 * Stores the range and results assigned to one thread.
 */
typedef struct {
    long start;
    long end;
    long *primes;
    long count;
    long capacity;
} ThreadData;

/*
 * Returns 1 if k is prime, otherwise returns 0.
 *
 * Optimisations:
 * - Numbers below 2 are immediately rejected.
 * - Even numbers greater than 2 are immediately rejected.
 * - Only odd divisors up to sqrt(k) are checked.
 */
int is_prime(long k) {
    if (k < 2)
        return 0;

    if (k == 2)
        return 1;

    if (k % 2 == 0)
        return 0;

    for (long i = 3; i * i <= k; i += 2) {
        if (k % i == 0)
            return 0;
    }

    return 1;
}

/*
 * Adds a prime to the thread's local result array.
 *
 * If the array is full, its capacity is doubled.
 */
void add_prime(ThreadData *data, long prime) {
    if (data->count == data->capacity) {
        data->capacity *= 2;

        long *new_primes =
            realloc(data->primes,
                    data->capacity * sizeof(long));

        if (new_primes == NULL) {
            fprintf(stderr, "Memory allocation failed.\n");
            exit(EXIT_FAILURE);
        }

        data->primes = new_primes;
    }

    data->primes[data->count++] = prime;
}

/*
 * Thread function.
 *
 * Each thread searches only its assigned range and stores
 * its prime numbers in its own local array.
 *
 * Optimisation:
 * - Skip even numbers entirely.
 */
void *find_primes(void *arg) {
    ThreadData *data = (ThreadData *)arg;

    long start = data->start;

    /* Handle the number 2 separately. */
    if (start <= 2 && data->end > 2) {
        add_prime(data, 2);
    }

    if (start < 3)
        start = 3;

    if (start % 2 == 0)
        start++;

    for (long k = start; k < data->end; k += 2) {
        if (is_prime(k)) {
            add_prime(data, k);
        }
    }

    return NULL;
}

int main(void) {
    long n;
    int num_threads;

    printf("Enter n (find primes strictly less than n): ");
    if (scanf("%ld", &n) != 1) {
        fprintf(stderr, "Invalid input.\n");
        return 1;
    }

    if (n <= 2) {
        printf("No primes strictly less than %ld.\n", n);
        return 0;
    }

    printf("Enter number of threads: ");
    if (scanf("%d", &num_threads) != 1 ||
        num_threads <= 0) {
        fprintf(stderr, "Invalid number of threads.\n");
        return 1;
    }

    pthread_t *threads =
        malloc(num_threads * sizeof(pthread_t));

    ThreadData *data =
        malloc(num_threads * sizeof(ThreadData));

    if (threads == NULL || data == NULL) {
        fprintf(stderr, "Memory allocation failed.\n");
        free(threads);
        free(data);
        return 1;
    }

    /*
     * There are n - 2 candidate numbers:
     *     2, 3, ..., n - 1
     *
     * Divide these as evenly as possible.
     */
    long total_numbers = n - 2;
    long base_size = total_numbers / num_threads;
    long remainder = total_numbers % num_threads;

    long current = 2;

    /*
     * Allocate memory for each thread before timing.
     */
    for (int i = 0; i < num_threads; i++) {

        long range_size = base_size;
        if (i < remainder)
            range_size++;

        data[i].start = current;
        data[i].end = current + range_size;

        data[i].count = 0;
        data[i].capacity = 1024;

        data[i].primes =
            malloc(data[i].capacity * sizeof(long));

        if (data[i].primes == NULL) {
            fprintf(stderr, "Memory allocation failed.\n");
            return 1;
        }

        current = data[i].end;
    }

    /*
     * Measure only the parallel computation.
     */
    struct timespec start_time, end_time;
    clock_gettime(CLOCK_MONOTONIC, &start_time);

    /*
     * Create threads.
     */
    for (int i = 0; i < num_threads; i++) {
        if (pthread_create(&threads[i],
                           NULL,
                           find_primes,
                           &data[i]) != 0) {
            fprintf(stderr,
                    "Failed to create thread %d.\n",
                    i);
            return 1;
        }
    }

    /*
     * Wait for all threads.
     */
    for (int i = 0; i < num_threads; i++) {
        if (pthread_join(threads[i], NULL) != 0) {
            fprintf(stderr,
                    "Failed to join thread %d.\n",
                    i);
            return 1;
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end_time);

    double elapsed =
        (end_time.tv_sec - start_time.tv_sec) +
        (end_time.tv_nsec - start_time.tv_nsec) / 1e9;

    /*
     * Output results after timing so file I/O does not
     * affect the measured parallel speedup.
     */
    int writing_to_file = (n >= 100);
    FILE *out;

    if (writing_to_file) {
        out = fopen("primes_output.txt", "w");

        if (out == NULL) {
            fprintf(stderr,
                    "Could not open output file.\n");
            return 1;
        }
    } else {
        out = stdout;
    }

    for (int i = 0; i < num_threads; i++) {

        for (long j = 0; j < data[i].count; j++) {
            fprintf(out, "%ld\n", data[i].primes[j]);
        }

        free(data[i].primes);
    }

    if (writing_to_file) {
        fclose(out);
        printf("Results written to primes_output.txt\n");
    }

    printf("Threads used: %d\n", num_threads);
    printf("Parallel computation time: %.6f seconds\n",
           elapsed);

    free(threads);
    free(data);

    return 0; 
}