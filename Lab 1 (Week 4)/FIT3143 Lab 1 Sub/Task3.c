#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <omp.h>

int is_prime(long k) {
    if (k < 2) { // numbers less than 2 are not prime
        return 0;
    }
    if (k == 2) { // 2 is prime
        return 1;
    }
    if (k % 2 == 0) { // even numbers greater than 2 are not prime
        return 0;
    }

    long limit = (long)sqrt((double)k); // only check for factors up to the square root of k
    for (long i = 3; i <= limit; i += 2) { // check only odd numbers
        if (k % i == 0) {
            return 0;
        }
    }
    return 1;
}

int main(void) {
    long n; // long is used to handle larger values of n

    printf("Enter n (find primes strictly less than n): ");
    if (scanf("%ld", &n) != 1) { // checks if the input is a valid long integer
        fprintf(stderr, "Invalid input.\n");
        return 1;
    }

    if (n <= 2) { // no primes strictly less than 2
        printf("No primes strictly less than %ld.\n", n);
        return 0;
    }

    FILE *out; // declare a file pointer for output
    int writing_to_file = (n >= 100); // decide whether to write to a file based on the value of n

    if (writing_to_file) { // if n is 100 or greater, write to a file
        out = fopen("primes_output.txt", "w");
        if (out == NULL) {
            fprintf(stderr, "Could not open output file.\n");
            return 1;
        }
    } else { // if n is less than 100, write to standard output
        out = stdout;
    }

    // flag array so each thread can record its own results without contending
    // over the shared output stream; index k holds whether k is prime
    char *is_p = malloc((size_t)n * sizeof(char));
    if (is_p == NULL) {
        fprintf(stderr, "Could not allocate memory.\n");
        return 1;
    }

    struct timespec start, end; // declare variables to hold the start and end times for measuring execution time
    clock_gettime(CLOCK_MONOTONIC, &start); // get the current time before starting the prime search

    // parallel primality testing: each thread independently tests a subset of k values.
    // dynamic scheduling is used because larger k takes longer to test (trial division
    // up to sqrt(k)), so an equal static split would leave later threads with more work.
    #pragma omp parallel for schedule(dynamic, 1000)
    for (long k = 2; k < n; k++) {
        is_p[k] = (char)is_prime(k);
    }

    // sequential pass to print in ascending order; cheap (O(n)) relative to the
    // parallel primality testing above, so it is not itself parallelized.
    // 2 is handled separately since it's the only even prime, then only odd
    // indices are checked, since no even k > 2 can be prime.
    if (is_p[2]) {
        fprintf(out, "2\n");
    }
    for (long k = 3; k < n; k += 2) {
        if (is_p[k]) {
            fprintf(out, "%ld\n", k);
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end); // get the current time after finishing the prime search
    double elapsed = (end.tv_sec - start.tv_sec) +
                      (end.tv_nsec - start.tv_nsec) / 1e9;

    free(is_p);

    if (writing_to_file) {
        fclose(out);
        printf("Results written to primes_output.txt\n");
    }

    printf("Time taken: %.6f seconds\n", elapsed);
    printf("Threads used: %d\n", omp_get_max_threads());

    return 0;
}
