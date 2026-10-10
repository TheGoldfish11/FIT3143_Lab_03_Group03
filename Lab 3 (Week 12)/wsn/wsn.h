// FIT3143 Lab 3 - Distributed Wireless Sensor Network (EV charging grid)
// Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
//
// Shared definitions for the EV charging nodes (node.c) and base station (base.c).

#ifndef WSN_H
#define WSN_H

#include <mpi.h>
#include <time.h>

#define MAX_PORTS       64    // upper bound on k (ports per node)
#define MAX_NBRS        4     // up, down, left, right in a 2D Cartesian grid
#define MAX_CANDIDATES  64    // upper bound on nearest nodes returned by the base station
#define HISTORY_LEN     256   // availability snapshots kept per node (ring buffer)
#define SEND_POOL_SIZE  64    // outstanding non-blocking sends per process
#define TIMESTAMP_LEN   20    // "YYYY-MM-DD HH:MM:SS" + '\0'

// message tags - one per message type, so each type can be counted and timed separately
enum {
    TAG_NBR_REQ = 1,     // node -> neighbour: "send me your availability"
    TAG_NBR_RESP,        // neighbour -> node: availability reply
    TAG_REPORT,          // node -> base: congestion alert (node and all neighbours full)
    TAG_BASE_REPLY,      // base -> node: nearest available nodes (or none)
    TAG_TERMINATE,       // base -> node: stop starting new work, then ack
    TAG_TERM_ACK,        // node -> base: stopped, carries the node's message statistics
    TAG_FINAL,           // base -> node: everyone has stopped, safe to exit
    NUM_TAGS
};

// simulation parameters, parsed from the command line on every rank
typedef struct {
    int    m, n;           // grid rows and columns
    int    k;              // charging ports per node
    int    threshold;      // a node is congested when availability <= threshold
    int    cycle_ms;       // port update / availability check cycle
    double duration_s;     // how long the base station runs the simulation
    double window_s;       // base station "recent report" window
    double p_arrive;       // per cycle chance a free port becomes in use
    double p_depart;       // per cycle chance an in-use port becomes free
    int    poll_us;        // sleep between MPI_Iprobe polls
    unsigned int seed;
    int    verbose;
    char   log_path[256];
} config_t;

// ---- message payloads (each sent as one MPI derived datatype) ----

typedef struct {
    int    node_id;
    double t_sent;         // requester's MPI_Wtime when sent, echoed back for round-trip time
} nbr_req_t;

typedef struct {
    int    node_id;
    int    avail;
    double t_req_sent;     // echoed from the request
} nbr_resp_t;

typedef struct {
    int    node_id, x, y;
    int    k, avail;
    int    n_nbrs;
    int    nbr_id[MAX_NBRS];
    int    nbr_avail[MAX_NBRS];
    int    msgs_exchanged;     // neighbour messages (requests + replies) for this incident
    int    bytes_exchanged;    // and their total size in bytes
    int    report_seq;         // n-th report from this node
    long   epoch_detected;     // seconds since epoch when congestion was detected
    double t_sent;             // node's MPI_Wtime when sent, echoed back for round-trip time
    char   timestamp[TIMESTAMP_LEN];
} report_t;

typedef struct {
    int    report_seq;
    int    n_candidates;       // 0 = no nodes available nearby
    int    distance;           // hop distance of the candidates
    int    cand_id[MAX_CANDIDATES];
    int    cand_avail[MAX_CANDIDATES];  // last known availability, -1 if unknown
    double t_report_sent;      // echoed from the report
    double base_proc_s;        // time the base spent handling the report
} base_reply_t;

// round-trip time statistics for one message type
typedef struct {
    int    count;
    double sum, min, max;
} rtt_stat_t;

typedef struct {
    int        node_id;
    int        sent[NUM_TAGS];
    int        recv[NUM_TAGS];
    int        bytes_sent;
    int        congestion_events;   // times availability fell to the threshold
    int        redirects;           // times a neighbour had space
    int        reports;             // times all neighbours were full -> base station
    rtt_stat_t nbr_rtt;             // TAG_NBR_REQ -> TAG_NBR_RESP
    rtt_stat_t report_rtt;          // TAG_REPORT -> TAG_BASE_REPLY (minus base processing)
} node_stats_t;

// MPI datatypes for the structs above, built once by create_types()
typedef struct {
    MPI_Datatype nbr_req, nbr_resp, report, base_reply, node_stats;
} wsn_types_t;

// pool of buffers for non-blocking sends, so no process blocks on a send
typedef struct {
    MPI_Request req[SEND_POOL_SIZE];
    union {
        nbr_req_t    a;
        nbr_resp_t   b;
        report_t     c;
        base_reply_t d;
        node_stats_t e;
    } buf[SEND_POOL_SIZE];
} send_pool_t;

// common.c
int    parse_args(int argc, char **argv, config_t *cfg, int rank);
void   create_types(wsn_types_t *t);
void   free_types(wsn_types_t *t);
void   pool_init(send_pool_t *p);
int    pool_isend(send_pool_t *p, const void *msg, size_t len, MPI_Datatype type,
                  int dest, int tag, MPI_Comm comm);
void   pool_wait_all(send_pool_t *p);
void   format_timestamp(time_t t, char out[TIMESTAMP_LEN]);
void   rtt_add(rtt_stat_t *s, double v);
void   sleep_us(long us);

// node.c / base.c
void   run_node(const config_t *cfg, MPI_Comm grid_comm, const wsn_types_t *types);
void   run_base(const config_t *cfg, const wsn_types_t *types);

#endif
