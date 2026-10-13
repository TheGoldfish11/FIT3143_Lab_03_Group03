// FIT3143 Lab 3 - helpers shared by the EV charging nodes and the base station

#include "wsn.h"

#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void usage(const char *prog) {
    fprintf(stderr,
        "Usage: mpirun -np <m*n+1> %s -m <rows> -n <cols> [options]\n"
        "  -k <ports>      charging ports per node            (default 6, max %d)\n"
        "  -t <threshold>  congested when free ports <= this  (default 1)\n"
        "  -c <ms>         port update / check cycle in ms    (default 1000)\n"
        "  -d <s>          simulation duration in seconds     (default 20)\n"
        "  -w <s>          base station report window in s    (default 5)\n"
        "  -a <p>          chance a free port becomes in use  (default 0.6)\n"
        "  -r <p>          chance an in-use port becomes free (default 0.3)\n"
        "  -i <us>         MPI_Iprobe polling interval in us  (default 1000)\n"
        "  -s <seed>       random seed                        (default time)\n"
        "  -o <file>       base station log file              (default base_station.log)\n"
        "  -C <file>       append a CSV summary row to file   (default off)\n"
        "  -b <version>    base station: poll, block, irecv   (default poll)\n"
        "  -N <version>    nodes: nonblock, block             (default nonblock)\n"
        "  -v              print every node event\n",
        prog, MAX_PORTS);
}

static const char *BASE_MODES[] = {"poll", "block", "irecv"};
static const char *NODE_MODES[] = {"nonblock", "block"};

const char *base_mode_name(int mode) { return BASE_MODES[mode]; }
const char *node_mode_name(int mode) { return NODE_MODES[mode]; }

// returns the index of name in names, or -1
static int lookup(const char *name, const char **names, int count) {
    for (int i = 0; i < count; i++) {
        if (strcmp(name, names[i]) == 0) return i;
    }
    return -1;
}

// every rank parses the same argv, so no broadcast is needed
int parse_args(int argc, char **argv, config_t *cfg, int rank) {
    cfg->m = 0;
    cfg->n = 0;
    cfg->k = 6;
    cfg->threshold = 1;
    cfg->cycle_ms = 1000;
    cfg->duration_s = 20.0;
    cfg->window_s = 5.0;
    cfg->p_arrive = 0.6;
    cfg->p_depart = 0.3;
    cfg->poll_us = 1000;
    cfg->seed = (unsigned int)time(NULL);
    cfg->verbose = 0;
    cfg->base_mode = BASE_POLL;
    cfg->node_mode = NODE_NONBLOCK;
    strcpy(cfg->log_path, "base_station.log");
    cfg->csv_path[0] = '\0';

    int opt;
    while ((opt = getopt(argc, argv, "m:n:k:t:c:d:w:a:r:i:s:o:C:b:N:v")) != -1) {
        switch (opt) {
            case 'm': cfg->m = atoi(optarg); break;
            case 'n': cfg->n = atoi(optarg); break;
            case 'k': cfg->k = atoi(optarg); break;
            case 't': cfg->threshold = atoi(optarg); break;
            case 'c': cfg->cycle_ms = atoi(optarg); break;
            case 'd': cfg->duration_s = atof(optarg); break;
            case 'w': cfg->window_s = atof(optarg); break;
            case 'a': cfg->p_arrive = atof(optarg); break;
            case 'r': cfg->p_depart = atof(optarg); break;
            case 'i': cfg->poll_us = atoi(optarg); break;
            case 's': cfg->seed = (unsigned int)strtoul(optarg, NULL, 10); break;
            case 'o':
                strncpy(cfg->log_path, optarg, sizeof(cfg->log_path) - 1);
                cfg->log_path[sizeof(cfg->log_path) - 1] = '\0';
                break;
            case 'C':
                strncpy(cfg->csv_path, optarg, sizeof(cfg->csv_path) - 1);
                cfg->csv_path[sizeof(cfg->csv_path) - 1] = '\0';
                break;
            case 'b':
                cfg->base_mode = lookup(optarg, BASE_MODES, 3);
                break;
            case 'N':
                cfg->node_mode = lookup(optarg, NODE_MODES, 2);
                break;
            case 'v': cfg->verbose = 1; break;
            default:
                if (rank == 0) usage(argv[0]);
                return 0;
        }
    }

    if (cfg->m < 1 || cfg->n < 1 || cfg->k < 1 || cfg->k > MAX_PORTS ||
        cfg->threshold < 0 || cfg->threshold >= cfg->k || cfg->cycle_ms < 1 ||
        cfg->duration_s <= 0 || cfg->window_s < 0 || cfg->poll_us < 0 ||
        cfg->base_mode < 0 || cfg->node_mode < 0) {
        if (rank == 0) usage(argv[0]);
        return 0;
    }
    return 1;
}

// builds a struct datatype and resizes it to sizeof(struct) so arrays/padding stay correct
static void make_struct(int count, int *blocklens, MPI_Aint *disps, MPI_Datatype *types,
                        size_t extent, MPI_Datatype *out) {
    MPI_Datatype tmp;
    MPI_Type_create_struct(count, blocklens, disps, types, &tmp);
    MPI_Type_create_resized(tmp, 0, (MPI_Aint)extent, out);
    MPI_Type_commit(out);
    MPI_Type_free(&tmp);
}

void create_types(wsn_types_t *t) {
    {
        int          bl[] = {1, 1};
        MPI_Aint     d[]  = {offsetof(nbr_req_t, node_id), offsetof(nbr_req_t, t_sent)};
        MPI_Datatype ty[] = {MPI_INT, MPI_DOUBLE};
        make_struct(2, bl, d, ty, sizeof(nbr_req_t), &t->nbr_req);
    }
    {
        int          bl[] = {2, 1};
        MPI_Aint     d[]  = {offsetof(nbr_resp_t, node_id), offsetof(nbr_resp_t, t_req_sent)};
        MPI_Datatype ty[] = {MPI_INT, MPI_DOUBLE};
        make_struct(2, bl, d, ty, sizeof(nbr_resp_t), &t->nbr_resp);
    }
    {
        // node_id .. report_seq are 17 consecutive ints
        int          bl[] = {17, 1, 1, TIMESTAMP_LEN};
        MPI_Aint     d[]  = {offsetof(report_t, node_id), offsetof(report_t, epoch_detected),
                             offsetof(report_t, t_sent), offsetof(report_t, timestamp)};
        MPI_Datatype ty[] = {MPI_INT, MPI_LONG, MPI_DOUBLE, MPI_CHAR};
        make_struct(4, bl, d, ty, sizeof(report_t), &t->report);
    }
    {
        int          bl[] = {3 + 2 * MAX_CANDIDATES, 2};
        MPI_Aint     d[]  = {offsetof(base_reply_t, report_seq),
                             offsetof(base_reply_t, t_report_sent)};
        MPI_Datatype ty[] = {MPI_INT, MPI_DOUBLE};
        make_struct(2, bl, d, ty, sizeof(base_reply_t), &t->base_reply);
    }
    {
        int          bl[] = {1 + 2 * NUM_TAGS + 4, 1, 3, 1, 3, 1};
        MPI_Aint     d[]  = {offsetof(node_stats_t, node_id),
                             offsetof(node_stats_t, nbr_rtt.count),
                             offsetof(node_stats_t, nbr_rtt.sum),
                             offsetof(node_stats_t, report_rtt.count),
                             offsetof(node_stats_t, report_rtt.sum),
                             offsetof(node_stats_t, ctrl_cpu_s)};
        MPI_Datatype ty[] = {MPI_INT, MPI_INT, MPI_DOUBLE, MPI_INT, MPI_DOUBLE, MPI_DOUBLE};
        make_struct(6, bl, d, ty, sizeof(node_stats_t), &t->node_stats);
    }
}

void free_types(wsn_types_t *t) {
    MPI_Type_free(&t->nbr_req);
    MPI_Type_free(&t->nbr_resp);
    MPI_Type_free(&t->report);
    MPI_Type_free(&t->base_reply);
    MPI_Type_free(&t->node_stats);
}

void pool_init(send_pool_t *p) {
    for (int i = 0; i < SEND_POOL_SIZE; i++) {
        p->req[i] = MPI_REQUEST_NULL;
    }
}

// copies msg into a free slot and starts an MPI_Isend from it, so the caller never blocks
// waiting for the receiver; returns the payload size in bytes
int pool_isend(send_pool_t *p, const void *msg, size_t len, MPI_Datatype type,
               int dest, int tag, MPI_Comm comm) {
    int slot = -1;
    for (int i = 0; i < SEND_POOL_SIZE && slot < 0; i++) {
        int done = 1;
        if (p->req[i] != MPI_REQUEST_NULL) {
            MPI_Test(&p->req[i], &done, MPI_STATUS_IGNORE);
        }
        if (done) slot = i;
    }
    if (slot < 0) {
        // every slot is still in flight, wait for the first one to finish
        MPI_Waitany(SEND_POOL_SIZE, p->req, &slot, MPI_STATUS_IGNORE);
    }

    memcpy(&p->buf[slot], msg, len);
    MPI_Isend(&p->buf[slot], 1, type, dest, tag, comm, &p->req[slot]);

    int bytes;
    MPI_Type_size(type, &bytes);
    return bytes;
}

// blocking versions send straight from msg with MPI_Send; the others go through the pool
int msg_send(send_pool_t *p, int blocking, const void *msg, size_t len, MPI_Datatype type,
             int dest, int tag, MPI_Comm comm) {
    if (!blocking) return pool_isend(p, msg, len, type, dest, tag, comm);

    MPI_Send(msg, 1, type, dest, tag, comm);
    int bytes;
    MPI_Type_size(type, &bytes);
    return bytes;
}

void pool_wait_all(send_pool_t *p) {
    MPI_Waitall(SEND_POOL_SIZE, p->req, MPI_STATUSES_IGNORE);
}

void format_timestamp(time_t t, char out[TIMESTAMP_LEN]) {
    struct tm tm_local;
    localtime_r(&t, &tm_local);
    strftime(out, TIMESTAMP_LEN, "%Y-%m-%d %H:%M:%S", &tm_local);
}

void rtt_add(rtt_stat_t *s, double v) {
    if (s->count == 0 || v < s->min) s->min = v;
    if (s->count == 0 || v > s->max) s->max = v;
    s->sum += v;
    s->count++;
}

void sleep_us(long us) {
    if (us <= 0) return;
    struct timespec ts = {us / 1000000, (us % 1000000) * 1000};
    nanosleep(&ts, NULL);
}

// CPU time (not wall time) used so far by the calling thread / the whole process
double thread_cpu_s(void) {
    struct timespec ts;
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

double process_cpu_s(void) {
    struct timespec ts;
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}
