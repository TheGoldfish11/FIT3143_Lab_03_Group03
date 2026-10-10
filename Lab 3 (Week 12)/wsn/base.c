// FIT3143 Lab 3 - Task 2: base station
//
// A single MPI process with a single thread. It polls for reports with MPI_Iprobe, works out
// the nearest available nodes for each report, logs everything, and at the end of the
// simulation runs the two-phase shutdown (TERMINATE -> TERM_ACK from every node -> FINAL).

#include "wsn.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *TAG_NAMES[NUM_TAGS] = {
    "", "NBR_REQ", "NBR_RESP", "REPORT", "BASE_REPLY", "TERMINATE", "TERM_ACK", "FINAL"
};

typedef struct {
    const config_t    *cfg;
    const wsn_types_t *types;
    int                num_nodes;
    FILE              *log;
    send_pool_t        pool;
    double             t_start;

    // what the base station knows about each node
    double *last_report;    // MPI_Wtime of the node's last report, < 0 if never
    int    *known_avail;    // availability from the latest report that mentioned the node
    double *known_time;     // when that was, < 0 if never

    node_stats_t *node_stats;   // filled in from each node's TERM_ACK
    int           acks;

    int    alerts;
    int    replies_with_nodes;
    int    replies_none;
    int    recv[NUM_TAGS];
    int    sent[NUM_TAGS];
} base_t;

static int manhattan(const base_t *b, int a, int c) {
    int n = b->cfg->n;
    return abs(a / n - c / n) + abs(a % n - c % n);
}

static int recent(const base_t *b, double t, double now) {
    return t >= 0 && now - t <= b->cfg->window_s;
}

// a node is ruled out if it reported recently, or a recent report showed it congested
static int maybe_available(const base_t *b, int node, double now) {
    if (recent(b, b->last_report[node], now)) return 0;
    if (recent(b, b->known_time[node], now) && b->known_avail[node] <= b->cfg->threshold) return 0;
    return 1;
}

static void handle_report(base_t *b, const report_t *rep, int source) {
    double t0 = MPI_Wtime();
    double now = t0;
    b->alerts++;

    // check before recording this report: had every neighbour of the reporter already
    // reported within the window? Their reports also covered the nodes two hops away.
    int all_nbrs_reported = 1;
    for (int i = 0; i < rep->n_nbrs; i++) {
        if (!recent(b, b->last_report[rep->nbr_id[i]], now)) all_nbrs_reported = 0;
    }

    b->last_report[rep->node_id] = now;
    b->known_avail[rep->node_id] = rep->avail;
    b->known_time[rep->node_id] = now;
    for (int i = 0; i < rep->n_nbrs; i++) {
        b->known_avail[rep->nbr_id[i]] = rep->nbr_avail[i];
        b->known_time[rep->nbr_id[i]] = now;
    }

    base_reply_t reply;
    memset(&reply, 0, sizeof(reply));
    reply.report_seq = rep->report_seq;
    reply.t_report_sent = rep->t_sent;

    if (!all_nbrs_reported) {
        // search outwards from two hops; every node at the smallest distance is returned
        int max_d = (b->cfg->m - 1) + (b->cfg->n - 1);
        for (int d = 2; d <= max_d && reply.n_candidates == 0; d++) {
            for (int node = 0; node < b->num_nodes; node++) {
                if (manhattan(b, rep->node_id, node) == d && maybe_available(b, node, now) &&
                    reply.n_candidates < MAX_CANDIDATES) {
                    int c = reply.n_candidates++;
                    reply.cand_id[c] = node;
                    reply.cand_avail[c] = recent(b, b->known_time[node], now) ? b->known_avail[node] : -1;
                    reply.distance = d;
                }
            }
        }
    }

    if (reply.n_candidates > 0) b->replies_with_nodes++;
    else b->replies_none++;

    reply.base_proc_s = MPI_Wtime() - t0;
    pool_isend(&b->pool, &reply, sizeof(reply), b->types->base_reply, source,
               TAG_BASE_REPLY, MPI_COMM_WORLD);
    b->sent[TAG_BASE_REPLY]++;

    // log entry
    FILE *f = b->log;
    char logged[TIMESTAMP_LEN];
    format_timestamp(time(NULL), logged);
    fprintf(f, "------------------------------------------------------------\n");
    fprintf(f, "Alert #%d   logged %s   sim time %.3f s\n", b->alerts, logged, now - b->t_start);
    fprintf(f, "Reporter        : node %d (%d,%d), report #%d\n",
            rep->node_id, rep->x, rep->y, rep->report_seq);
    fprintf(f, "Detected at     : %s\n", rep->timestamp);
    fprintf(f, "Availability    : %d/%d free\n", rep->avail, rep->k);
    fprintf(f, "Neighbours      :");
    for (int i = 0; i < rep->n_nbrs; i++) {
        int id = rep->nbr_id[i];
        fprintf(f, " node %d (%d,%d) %d/%d free%s", id, id / b->cfg->n, id % b->cfg->n,
                rep->nbr_avail[i], rep->k, i + 1 < rep->n_nbrs ? ";" : "");
    }
    fprintf(f, "\nNeighbour msgs  : %d messages, %d bytes\n",
            rep->msgs_exchanged, rep->bytes_exchanged);
    if (all_nbrs_reported) {
        fprintf(f, "Decision        : all neighbours reported within %.1f s -> no nodes available nearby\n",
                b->cfg->window_s);
    } else if (reply.n_candidates == 0) {
        fprintf(f, "Decision        : no available node found in the grid\n");
    } else {
        fprintf(f, "Decision        : %d nearest node(s) at distance %d:",
                reply.n_candidates, reply.distance);
        for (int i = 0; i < reply.n_candidates; i++) {
            int id = reply.cand_id[i];
            fprintf(f, " %d (%d,%d)", id, id / b->cfg->n, id % b->cfg->n);
            if (reply.cand_avail[i] >= 0) fprintf(f, " [%d free]", reply.cand_avail[i]);
        }
        fprintf(f, "\n");
    }
}

// receives and handles every message that has already arrived, without blocking
static int service_messages(base_t *b) {
    int handled = 0;
    int flag;
    MPI_Status st;

    MPI_Iprobe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &st);
    while (flag) {
        handled++;
        b->recv[st.MPI_TAG]++;

        if (st.MPI_TAG == TAG_REPORT) {
            report_t rep;
            MPI_Recv(&rep, 1, b->types->report, st.MPI_SOURCE, TAG_REPORT,
                     MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            handle_report(b, &rep, st.MPI_SOURCE);
        } else if (st.MPI_TAG == TAG_TERM_ACK) {
            node_stats_t s;
            MPI_Recv(&s, 1, b->types->node_stats, st.MPI_SOURCE, TAG_TERM_ACK,
                     MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            b->node_stats[st.MPI_SOURCE] = s;
            b->acks++;
        } else {
            fprintf(stderr, "[base] unexpected tag %d from %d\n", st.MPI_TAG, st.MPI_SOURCE);
            MPI_Recv(NULL, 0, MPI_BYTE, st.MPI_SOURCE, st.MPI_TAG,
                     MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        }
        MPI_Iprobe(MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &st);
    }
    return handled;
}

static void broadcast_control(base_t *b, int tag) {
    MPI_Request *reqs = malloc(sizeof(MPI_Request) * (size_t)b->num_nodes);
    for (int i = 0; i < b->num_nodes; i++) {
        MPI_Isend(NULL, 0, MPI_INT, i, tag, MPI_COMM_WORLD, &reqs[i]);
    }
    MPI_Waitall(b->num_nodes, reqs, MPI_STATUSES_IGNORE);
    b->sent[tag] += b->num_nodes;
    free(reqs);
}

static void write_summary(base_t *b, double sim_time) {
    FILE *f = b->log;
    long nbr_msgs = 0;
    int events = 0, redirects = 0;
    rtt_stat_t nbr_rtt = {0}, rep_rtt = {0};

    for (int i = 0; i < b->num_nodes; i++) {
        node_stats_t *s = &b->node_stats[i];
        nbr_msgs += s->sent[TAG_NBR_REQ] + s->sent[TAG_NBR_RESP];
        events += s->congestion_events;
        redirects += s->redirects;
        if (s->nbr_rtt.count) {
            if (nbr_rtt.count == 0 || s->nbr_rtt.min < nbr_rtt.min) nbr_rtt.min = s->nbr_rtt.min;
            if (s->nbr_rtt.max > nbr_rtt.max) nbr_rtt.max = s->nbr_rtt.max;
            nbr_rtt.sum += s->nbr_rtt.sum;
            nbr_rtt.count += s->nbr_rtt.count;
        }
        if (s->report_rtt.count) {
            if (rep_rtt.count == 0 || s->report_rtt.min < rep_rtt.min) rep_rtt.min = s->report_rtt.min;
            if (s->report_rtt.max > rep_rtt.max) rep_rtt.max = s->report_rtt.max;
            rep_rtt.sum += s->report_rtt.sum;
            rep_rtt.count += s->report_rtt.count;
        }
    }

    long base_recv = 0, base_sent = 0;
    for (int t = 1; t < NUM_TAGS; t++) {
        base_recv += b->recv[t];
        base_sent += b->sent[t];
    }

    fprintf(f, "============================================================\n");
    fprintf(f, "SUMMARY\n");
    fprintf(f, "Simulation time         : %.3f s\n", sim_time);
    fprintf(f, "Congestion events       : %d (nodes at or below threshold)\n", events);
    fprintf(f, "Redirected to neighbour : %d\n", redirects);
    fprintf(f, "Alerts to base station  : %d (%d with nearest nodes, %d none nearby)\n",
            b->alerts, b->replies_with_nodes, b->replies_none);
    fprintf(f, "Total messages          : %ld (%ld node<->node, %ld to base, %ld from base)\n",
            nbr_msgs + base_recv + base_sent, nbr_msgs, base_recv, base_sent);
    fprintf(f, "Messages by type        :\n");
    for (int t = 1; t < NUM_TAGS; t++) {
        long count = b->recv[t] + b->sent[t];
        if (t == TAG_NBR_REQ || t == TAG_NBR_RESP) {
            count = 0;
            for (int i = 0; i < b->num_nodes; i++) count += b->node_stats[i].sent[t];
        }
        fprintf(f, "  %-12s %ld\n", TAG_NAMES[t], count);
    }
    fprintf(f, "Round-trip times (s)    :     count        avg        min        max\n");
    fprintf(f, "  NBR_REQ -> NBR_RESP     %9d %10.6f %10.6f %10.6f\n", nbr_rtt.count,
            nbr_rtt.count ? nbr_rtt.sum / nbr_rtt.count : 0.0, nbr_rtt.min, nbr_rtt.max);
    fprintf(f, "  REPORT  -> BASE_REPLY   %9d %10.6f %10.6f %10.6f\n", rep_rtt.count,
            rep_rtt.count ? rep_rtt.sum / rep_rtt.count : 0.0, rep_rtt.min, rep_rtt.max);
    fprintf(f, "Per node                : node  (x,y)  events redirects reports\n");
    for (int i = 0; i < b->num_nodes; i++) {
        node_stats_t *s = &b->node_stats[i];
        fprintf(f, "                          %4d (%d,%d) %6d %9d %7d\n", i, i / b->cfg->n,
                i % b->cfg->n, s->congestion_events, s->redirects, s->reports);
    }

    printf("[base] %dx%d grid, %.2f s: %d alerts (%d with nodes, %d none nearby), "
           "%ld messages, log written to %s\n",
           b->cfg->m, b->cfg->n, sim_time, b->alerts, b->replies_with_nodes, b->replies_none,
           nbr_msgs + base_recv + base_sent, b->cfg->log_path);
}

void run_base(const config_t *cfg, const wsn_types_t *types) {
    base_t b;
    memset(&b, 0, sizeof(b));
    b.cfg = cfg;
    b.types = types;
    b.num_nodes = cfg->m * cfg->n;
    pool_init(&b.pool);

    b.last_report = malloc(sizeof(double) * (size_t)b.num_nodes);
    b.known_avail = malloc(sizeof(int) * (size_t)b.num_nodes);
    b.known_time = malloc(sizeof(double) * (size_t)b.num_nodes);
    b.node_stats = calloc((size_t)b.num_nodes, sizeof(node_stats_t));
    b.log = fopen(cfg->log_path, "w");
    if (!b.last_report || !b.known_avail || !b.known_time || !b.node_stats || !b.log) {
        fprintf(stderr, "[base] could not allocate memory or open %s\n", cfg->log_path);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    for (int i = 0; i < b.num_nodes; i++) {
        b.last_report[i] = -1;
        b.known_avail[i] = -1;
        b.known_time[i] = -1;
    }

    char started[TIMESTAMP_LEN];
    format_timestamp(time(NULL), started);
    fprintf(b.log, "EV charging WSN - base station log\n");
    fprintf(b.log, "Started %s\n", started);
    fprintf(b.log, "Grid %dx%d (%d nodes), k=%d ports, threshold=%d, cycle=%d ms, "
                   "duration=%.1f s, window=%.1f s, p_arrive=%.2f, p_depart=%.2f, poll=%d us, seed=%u\n",
            cfg->m, cfg->n, b.num_nodes, cfg->k, cfg->threshold, cfg->cycle_ms, cfg->duration_s,
            cfg->window_s, cfg->p_arrive, cfg->p_depart, cfg->poll_us, cfg->seed);

    b.t_start = MPI_Wtime();
    while (MPI_Wtime() - b.t_start < cfg->duration_s) {
        if (!service_messages(&b)) sleep_us(cfg->poll_us);
    }

    // phase 1: nodes stop starting incidents; keep answering reports until everyone acks
    broadcast_control(&b, TAG_TERMINATE);
    while (b.acks < b.num_nodes) {
        if (!service_messages(&b)) sleep_us(cfg->poll_us);
    }
    // phase 2: no node can send anything new now, so everyone can exit
    broadcast_control(&b, TAG_FINAL);
    pool_wait_all(&b.pool);

    write_summary(&b, MPI_Wtime() - b.t_start);

    fclose(b.log);
    free(b.last_report);
    free(b.known_avail);
    free(b.known_time);
    free(b.node_stats);
}
