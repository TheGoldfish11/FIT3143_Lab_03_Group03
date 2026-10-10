// FIT3143 Lab 3 - Distributed Wireless Sensor Network (EV charging grid)
// Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
//
// Ranks 0 .. m*n-1 are EV charging nodes laid out on an m x n MPI Cartesian topology
// (rank = x*n + y, so Node 1 = (0,1) as in the spec). Rank m*n is the base station.

#include "wsn.h"

#include <stdio.h>

int main(int argc, char **argv) {
    // only the main thread of each process makes MPI calls, port threads never do
    int provided;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (provided < MPI_THREAD_FUNNELED) {
        if (rank == 0) fprintf(stderr, "MPI library does not support MPI_THREAD_FUNNELED\n");
        MPI_Finalize();
        return 1;
    }

    config_t cfg;
    if (!parse_args(argc, argv, &cfg, rank)) {
        MPI_Finalize();
        return 1;
    }

    int num_nodes = cfg.m * cfg.n;
    if (size != num_nodes + 1) {
        if (rank == 0) {
            fprintf(stderr, "Need m*n+1 = %d processes for a %dx%d grid, got %d\n",
                    num_nodes + 1, cfg.m, cfg.n, size);
        }
        MPI_Finalize();
        return 1;
    }

    wsn_types_t types;
    create_types(&types);

    // split the charging nodes off from the base station; key = rank keeps the same order
    int base_rank = num_nodes;
    MPI_Comm nodes_comm;
    MPI_Comm_split(MPI_COMM_WORLD, rank == base_rank ? MPI_UNDEFINED : 0, rank, &nodes_comm);

    if (rank == base_rank) {
        run_base(&cfg, &types);
    } else {
        // reorder = 0 so a node's grid rank equals its world rank (its node ID)
        int dims[2] = {cfg.m, cfg.n};
        int periods[2] = {0, 0};
        MPI_Comm grid_comm;
        MPI_Cart_create(nodes_comm, 2, dims, periods, 0, &grid_comm);

        run_node(&cfg, grid_comm, &types);

        MPI_Comm_free(&grid_comm);
        MPI_Comm_free(&nodes_comm);
    }

    free_types(&types);
    MPI_Finalize();
    return 0;
}
