// FIT3143 Lab 3 - Task 1: EV charging node
//
// One MPI process per node. Inside the process, an OpenMP team of k+1 threads:
//   thread 0      - the only thread that calls MPI (MPI_THREAD_FUNNELED): checks availability
//                   every cycle, talks to neighbours and the base station
//   threads 1..k  - one per charging port, each updating its own slot of the shared array

#include "wsn.h"

#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    time_t t;
    int    avail;
} snapshot_t;

typedef struct {
    const config_t    *cfg;
    const wsn_types_t *types;
    int                id, x, y;
    int                base_rank;

    // shared between all threads of this node
    int        *port_in_use;   // shared array: port i is written only by port thread i
    int         running;       // cleared by thread 0 to stop the port threads

    // used by thread 0 only
    snapshot_t *history;       // availability every cycle, like Table 1 in the spec
    int         history_count;
    int         nbr[MAX_NBRS];
    int         n_nbrs;
    send_pool_t pool;
    node_stats_t stats;

    // current congestion incident
    int         round_active;
    int         replies_pending;
    int         reply_avail[MAX_NBRS];
    int         round_msgs, round_bytes;
    time_t      round_detected;
    int         awaiting_base;
} node_t;

static int availability(node_t *nd) {
    int free_ports = 0;
    for (int i = 0; i < nd->cfg->k; i++) {
        int in_use;
        #pragma omp atomic read
        in_use = nd->port_in_use[i];
        if (!in_use) free_ports++;
    }
    return free_ports;
}

static int still_running(node_t *nd) {
    int r;
    #pragma omp atomic read
    r = nd->running;
    return r;
}

// ---- port threads ----

static void port_loop(node_t *nd, int port) {
    const config_t *cfg = nd->cfg;
    unsigned int seed = cfg->seed ^ (unsigned int)(nd->id * 7919 + port * 104729 + 1);
    long cycle_us = (long)cfg->cycle_ms * 1000;
    long slice_us = 10000;   // wake up every 10 ms so shutdown is quick

    // stagger the ports so they do not all change at the same instant
    long wait_us = (long)(rand_r(&seed) % (unsigned int)cycle_us);

    while (still_running(nd)) {
        if (wait_us > 0) {
            long s = wait_us < slice_us ? wait_us : slice_us;
            sleep_us(s);
            wait_us -= s;
            continue;
        }
        wait_us = cycle_us;

        // an EV arrives at a free port, or leaves an in-use one
        double r = rand_r(&seed) / (double)RAND_MAX;
        int in_use;
        #pragma omp atomic read
        in_use = nd->port_in_use[port];
        #pragma omp atomic write
        nd->port_in_use[port] = in_use ? (r >= cfg->p_depart) : (r < cfg->p_arrive);
    }
}

// ---- thread 0: congestion handling ----

static void send_to(node_t *nd, const void *msg, size_t len, MPI_Datatype type, int dest, int tag) {
    int bytes = pool_isend(&nd->pool, msg, len, type, dest, tag, MPI_COMM_WORLD);
    nd->stats.sent[tag]++;
    nd->stats.bytes_sent += bytes;
    if (tag == TAG_NBR_REQ) {   // replies we receive are counted in service_messages
        nd->round_msgs++;
        nd->round_bytes += bytes;
    }
}

static void start_round(node_t *nd, int avail) {
    nd->stats.congestion_events++;
    nd->round_active = 1;
    nd->replies_pending = nd->n_nbrs;
    nd->round_msgs = 0;
    nd->round_bytes = 0;
    nd->round_detected = time(NULL);

    if (nd->cfg->verbose) {
        printf("[node %d (%d,%d)] congested: %d/%d free, asking %d neighbours\n",
               nd->id, nd->x, nd->y, avail, nd->cfg->k, nd->n_nbrs);
    }

    nbr_req_t req = {nd->id, MPI_Wtime()};
    for (int i = 0; i < nd->n_nbrs; i++) {
        send_to(nd, &req, sizeof(req), nd->types->nbr_req, nd->nbr[i], TAG_NBR_REQ);
    }
}

static void finish_round(node_t *nd) {
    nd->round_active = 0;

    // redirect to the neighbour with the most free ports, if any has space
    int best = -1;
    for (int i = 0; i < nd->n_nbrs; i++) {
        if (nd->reply_avail[i] > nd->cfg->threshold &&
            (best < 0 || nd->reply_avail[i] > nd->reply_avail[best])) {
            best = i;
        }
    }
    if (best >= 0) {
        nd->stats.redirects++;
        if (nd->cfg->verbose) {
            printf("[node %d] redirecting EVs to neighbour %d (%d free)\n",
                   nd->id, nd->nbr[best], nd->reply_avail[best]);
        }
        return;
    }

    // every neighbour is congested too: one report message to the base station
    report_t rep;
    memset(&rep, 0, sizeof(rep));
    rep.node_id = nd->id;
    rep.x = nd->x;
    rep.y = nd->y;
    rep.k = nd->cfg->k;
    rep.avail = availability(nd);
    rep.n_nbrs = nd->n_nbrs;
    for (int i = 0; i < MAX_NBRS; i++) {
        rep.nbr_id[i] = i < nd->n_nbrs ? nd->nbr[i] : -1;
        rep.nbr_avail[i] = i < nd->n_nbrs ? nd->reply_avail[i] : -1;
    }
    rep.msgs_exchanged = nd->round_msgs;
    rep.bytes_exchanged = nd->round_bytes;
    rep.report_seq = ++nd->stats.reports;
    rep.epoch_detected = (long)nd->round_detected;
    format_timestamp(nd->round_detected, rep.timestamp);
    rep.t_sent = MPI_Wtime();

    send_to(nd, &rep, sizeof(rep), nd->types->report, nd->base_rank, TAG_REPORT);
    nd->awaiting_base = 1;

    if (nd->cfg->verbose) {
        printf("[node %d] all neighbours full, report #%d sent to base station\n",
               nd->id, rep.report_seq);
    }
}

// receives and handles every message that has already arrived, without blocking
static int service_messages(node_t *nd, int *terminating, int *final) {
    int handled = 0;
    int flag;
    MPI_Status st;

    MPI_Iprobe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &st);
    while (flag) {
        handled++;
        nd->stats.recv[st.MPI_TAG]++;

        switch (st.MPI_TAG) {
            case TAG_NBR_REQ: {
                nbr_req_t req;
                MPI_Recv(&req, 1, nd->types->nbr_req, st.MPI_SOURCE, TAG_NBR_REQ,
                         MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                nbr_resp_t resp = {nd->id, availability(nd), req.t_sent};
                send_to(nd, &resp, sizeof(resp), nd->types->nbr_resp, st.MPI_SOURCE, TAG_NBR_RESP);
                break;
            }
            case TAG_NBR_RESP: {
                nbr_resp_t resp;
                MPI_Recv(&resp, 1, nd->types->nbr_resp, st.MPI_SOURCE, TAG_NBR_RESP,
                         MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                rtt_add(&nd->stats.nbr_rtt, MPI_Wtime() - resp.t_req_sent);
                int b;
                MPI_Type_size(nd->types->nbr_resp, &b);
                nd->round_msgs++;
                nd->round_bytes += b;
                for (int i = 0; i < nd->n_nbrs; i++) {
                    if (nd->nbr[i] == resp.node_id) nd->reply_avail[i] = resp.avail;
                }
                if (nd->round_active && --nd->replies_pending == 0) {
                    finish_round(nd);
                }
                break;
            }
            case TAG_BASE_REPLY: {
                base_reply_t rep;
                MPI_Recv(&rep, 1, nd->types->base_reply, st.MPI_SOURCE, TAG_BASE_REPLY,
                         MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                rtt_add(&nd->stats.report_rtt, MPI_Wtime() - rep.t_report_sent - rep.base_proc_s);
                nd->awaiting_base = 0;
                if (nd->cfg->verbose) {
                    if (rep.n_candidates == 0) {
                        printf("[node %d] base station: no nodes available nearby\n", nd->id);
                    } else {
                        printf("[node %d] base station: forwarding %d nearest node(s) to EVs:",
                               nd->id, rep.n_candidates);
                        for (int i = 0; i < rep.n_candidates; i++) printf(" %d", rep.cand_id[i]);
                        printf("\n");
                    }
                }
                break;
            }
            case TAG_TERMINATE:
                MPI_Recv(NULL, 0, MPI_INT, st.MPI_SOURCE, TAG_TERMINATE,
                         MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                *terminating = 1;
                break;
            case TAG_FINAL:
                MPI_Recv(NULL, 0, MPI_INT, st.MPI_SOURCE, TAG_FINAL,
                         MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                *final = 1;
                break;
            default:
                fprintf(stderr, "[node %d] unexpected tag %d from %d\n",
                        nd->id, st.MPI_TAG, st.MPI_SOURCE);
                MPI_Recv(NULL, 0, MPI_BYTE, st.MPI_SOURCE, st.MPI_TAG,
                         MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        }
        MPI_Iprobe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &st);
    }
    return handled;
}

// Shutdown is two-phase so no message is left unreceived at MPI_Finalize:
//   TERMINATE -> stop starting incidents, wait for own neighbour replies, send TERM_ACK
//   FINAL     -> sent once every node has acked, so no new neighbour requests can exist
static void control_loop(node_t *nd) {
    const config_t *cfg = nd->cfg;
    double cycle_s = cfg->cycle_ms / 1000.0;
    double next_tick = MPI_Wtime() + cycle_s;
    int terminating = 0, acked = 0, final = 0;

    while (!final) {
        int handled = service_messages(nd, &terminating, &final);

        double now = MPI_Wtime();
        if (!terminating && now >= next_tick) {
            next_tick += cycle_s;

            int avail = availability(nd);
            snapshot_t *s = &nd->history[nd->history_count % HISTORY_LEN];
            s->t = time(NULL);
            s->avail = avail;
            nd->history_count++;

            if (avail <= cfg->threshold && !nd->round_active && !nd->awaiting_base) {
                start_round(nd, avail);
                if (nd->n_nbrs == 0) finish_round(nd);   // 1x1 grid
            }
        }

        if (terminating && !acked && !nd->round_active) {
            send_to(nd, &nd->stats, sizeof(nd->stats), nd->types->node_stats,
                    nd->base_rank, TAG_TERM_ACK);
            acked = 1;
        }

        if (!handled) sleep_us(cfg->poll_us);
    }
}

void run_node(const config_t *cfg, MPI_Comm grid_comm, const wsn_types_t *types) {
    node_t nd;
    memset(&nd, 0, sizeof(nd));
    nd.cfg = cfg;
    nd.types = types;
    nd.base_rank = cfg->m * cfg->n;
    nd.running = 1;
    pool_init(&nd.pool);

    MPI_Comm_rank(grid_comm, &nd.id);
    int coords[2];
    MPI_Cart_coords(grid_comm, nd.id, 2, coords);
    nd.x = coords[0];
    nd.y = coords[1];
    nd.stats.node_id = nd.id;

    // neighbours from the virtual topology: top/bottom (dim 0), left/right (dim 1)
    for (int dim = 0; dim < 2; dim++) {
        int lo, hi;
        MPI_Cart_shift(grid_comm, dim, 1, &lo, &hi);
        if (lo != MPI_PROC_NULL) nd.nbr[nd.n_nbrs++] = lo;
        if (hi != MPI_PROC_NULL) nd.nbr[nd.n_nbrs++] = hi;
    }

    nd.port_in_use = calloc((size_t)cfg->k, sizeof(int));
    nd.history = calloc(HISTORY_LEN, sizeof(snapshot_t));
    if (!nd.port_in_use || !nd.history) {
        fprintf(stderr, "[node %d] out of memory\n", nd.id);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    omp_set_dynamic(0);
    #pragma omp parallel num_threads(cfg->k + 1) shared(nd)
    {
        if (omp_get_thread_num() == 0) {
            if (omp_get_num_threads() != cfg->k + 1) {
                fprintf(stderr, "[node %d] needed %d threads, got %d\n",
                        nd.id, cfg->k + 1, omp_get_num_threads());
                MPI_Abort(MPI_COMM_WORLD, 1);
            }
            control_loop(&nd);
            #pragma omp atomic write
            nd.running = 0;
        } else {
            port_loop(&nd, omp_get_thread_num() - 1);
        }
    }

    pool_wait_all(&nd.pool);

    if (cfg->verbose) {
        printf("[node %d] done: %d cycles, %d congestion events, %d redirects, %d reports\n",
               nd.id, nd.history_count, nd.stats.congestion_events, nd.stats.redirects,
               nd.stats.reports);
    }

    free(nd.port_in_use);
    free(nd.history);
}
