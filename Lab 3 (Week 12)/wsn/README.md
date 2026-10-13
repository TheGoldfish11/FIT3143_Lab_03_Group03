# Lab 3 - EV charging WSN simulation (Tasks 1 and 2)

Julia Mallard, Nam Quang Tran - FIT3143 Lab 03, Group 03

## Build and run

```sh
make
mpirun -np 10 ./wsn -m 3 -n 3                 # 3x3 grid + base station = 10 processes
mpirun -np 10 ./wsn -m 3 -n 3 -a 0.8 -r 0.2 -v  # low availability test, print every event
mpirun -np 9  ./wsn -m 1 -n 8                 # line topology (Task 3b)
```

Always launch `m*n + 1` processes. On a laptop with fewer cores add `--oversubscribe`.

| Option | Meaning | Default |
|---|---|---|
| `-m`, `-n` | grid rows, columns (required) | |
| `-k` | charging ports per node (OpenMP threads) | 6 |
| `-t` | node is congested when free ports `<=` this | 1 |
| `-c` | port update / availability check cycle (ms) | 1000 |
| `-d` | simulation duration (s) | 20 |
| `-w` | base station "recent report" window (s) | 5 |
| `-a` / `-r` | per-cycle chance a port becomes in use / free | 0.6 / 0.3 |
| `-i` | `MPI_Iprobe` polling interval (us) | 1000 |
| `-s` | random seed | time |
| `-o` | base station log file | `base_station.log` |
| `-C` | append a one-line CSV summary of the run to this file | off |
| `-b` | base station version: `poll`, `block`, `irecv` (see below) | `poll` |
| `-N` | node version: `nonblock`, `block` (see below) | `nonblock` |
| `-v` | print node events to stdout | off |

`sample_logs/base_station_3x3.log` is an example base station log
(`-m 3 -n 3 -c 1000 -d 20 -w 5 -a 0.7 -r 0.3 -s 3143`).

## Files

| File | Contents |
|---|---|
| `main.c` | MPI init, splits base station from nodes, builds the Cartesian topology |
| `node.c` | Task 1 - EV charging node (MPI process + OpenMP port threads) |
| `base.c` | Task 2 - base station (single MPI process, single thread) |
| `common.c` | argument parsing, MPI derived datatypes, non-blocking send pool, CPU timers |
| `bench/bench_versions.sh` | runs every base station / node version combination, appends CSV rows |
| `bench/plot_versions.py` | graphs and a summary table from that CSV (needs matplotlib) |
| `wsn.h` | message tags, message structs, statistics |

## Architecture

```
MPI_COMM_WORLD
 ├─ ranks 0 .. m*n-1  ->  MPI_Comm_split  ->  MPI_Cart_create (m x n, non-periodic, reorder=0)
 │     EV charging node, rank = x*n + y   (Node 1 = (0,1), as in the spec)
 │       OpenMP team of k+1 threads
 │         thread 0     : the only thread calling MPI (MPI_THREAD_FUNNELED)
 │         threads 1..k : one per port, each writes only its own slot of port_in_use[]
 └─ rank m*n          ->  base station (one process, one thread)
```

### Message types

| Tag | Direction | Payload |
|---|---|---|
| `NBR_REQ` | node -> neighbour | requester id, send time |
| `NBR_RESP` | neighbour -> node | id, free ports, echoed send time |
| `REPORT` | node -> base | timestamp, id, (x,y), own and neighbour availability, neighbour message count and bytes, send time |
| `BASE_REPLY` | base -> node | all nearest available nodes (or none), distance, base processing time |
| `TERMINATE` | base -> all nodes | empty |
| `TERM_ACK` | node -> base | node's message counts and round-trip times |
| `FINAL` | base -> all nodes | empty |
| `TIME_UP` | node 0 -> base | empty; only sent with the blocking base station (`-b block`) |

Each message is a single `MPI_Type_create_struct` datatype, so a report costs one message.

### Node (Task 1)

Every cycle thread 0 records availability (with a timestamp) into a history array. If free
ports `<=` threshold it sends `NBR_REQ` to its 2-4 Cartesian neighbours (`MPI_Cart_shift`).
When every reply has arrived:
- a neighbour has space: redirect EVs to the neighbour with the most free ports
- every neighbour is full: send one `REPORT` to the base station, then forward its reply to the EVs

In the default version, thread 0 never blocks. It polls with `MPI_Iprobe` and sends with
`MPI_Isend` from a buffer pool. A plain blocking receive for the reply would deadlock when two
neighbouring nodes are congested at the same time and each waits for the other's reply; the
blocking version (`-N block`) avoids this by handling every message while it waits.

### Base station (Task 2)

The base station (default version) polls for messages with `MPI_Iprobe`. For each report from node R:
1. If **every** neighbour of R reported within the window `-w`, reply "no nodes available nearby".
2. Otherwise search outward from 2 hops (Manhattan distance) and return **all** nodes at the
   smallest distance that have not reported recently and were not shown as congested in a
   recent report. For Node 0 in a 3x3 grid the 2-hop candidates are Nodes 2, 4 and 6.

The log file records every report and decision, then a summary at the end. The summary
covers simulation time, alerts, total messages and messages by type, round-trip times and
per-node counts.

### Graceful shutdown (two-phase)

1. When `-d` seconds have passed, the base station sends `TERMINATE` to every node. Nodes stop
   starting new incidents, finish any neighbour round in progress (including a base station
   reply they are owed), and send `TERM_ACK`. The base station keeps answering reports meanwhile.
2. Once all acks are in, no node can start a new neighbour request, so the base station sends
   `FINAL`. Each node stops its port threads, completes its outstanding `MPI_Isend`s, frees its
   memory and calls `MPI_Finalize`.

MPI guarantees that messages between the same pair of processes arrive in order. So a node
always receives its last `BASE_REPLY` before `FINAL`, and no message is left unreceived.

## Versions (blocking vs non-blocking)

The rubric asks for several versions, blocking and non-blocking, compared with measurements.
Each version is picked on the command line, so everything else (logic, messages, logging) is
identical between them.

**Base station (`-b`):**

| Version | How it receives | Trade-off |
|---|---|---|
| `poll` (default) | `MPI_Iprobe`, then `MPI_Recv` of what it found; sleeps `-i` us when idle | reacts within one poll interval; wakes up even when idle |
| `block` | `MPI_Probe` waits for the next message; replies with `MPI_Send` | reacts at once, but cannot check the clock while waiting, so node 0 sends `TIME_UP` at the end of the run. Open MPI's blocking calls busy-wait, so it uses a full core |
| `irecv` | one `MPI_Irecv` per message type posted in advance, checked with `MPI_Testany`, re-posted after each message; sleeps `-i` us when idle | a message can land straight in its buffer; outstanding receives are cancelled at shutdown |

**Nodes (`-N`):**

| Version | How a neighbour round runs |
|---|---|
| `nonblock` (default) | requests go out with `MPI_Isend`; replies are picked up on later passes of the polling loop |
| `block` | requests go out with `MPI_Send`, then thread 0 waits in `MPI_Probe` until every reply (and any base station reply) is in. It handles *every* message while waiting, including other nodes' requests. Waiting only for its own replies would deadlock when two neighbours are congested at the same time |

The blocking versions rely on Open MPI sending small messages eagerly (under 4 KB on shared
memory, 64 KB over TCP; the biggest message here is 540 B), so `MPI_Send` returns without waiting
for the receiver. With `MPI_Ssend`, two neighbours sending requests to each other at once would
deadlock.

### Benchmark

```sh
make
bench/bench_versions.sh                         # 4x4 grid, 15 s runs, 3 repeats -> results/versions.csv
python3 bench/plot_versions.py results/versions.csv
```

Settings can be changed with environment variables (`GRID_M`, `GRID_N`, `DURATION`, `REPEATS`,
`MPIRUN`, `OUT`), for example `REPEATS=5 MPIRUN="mpirun --oversubscribe" bench/bench_versions.sh`.
The same seed does not give identical runs, because thread timing changes which ports flip
before each check, so use several repeats.

`results/trial/` holds a first run made on a 4-core cloud container, heavily oversubscribed.
It shows the method works and the general pattern; rerun on CAAS or a laptop for the slides.

## Delay measurement hooks (for Task 3)

Nodes time `NBR_REQ -> NBR_RESP` and `REPORT -> BASE_REPLY` round trips on their own clock,
so no clock sync is needed. The base station's processing time is subtracted from the second
one. Each node sends its totals back in `TERM_ACK`, and they appear in the log summary.
Round-trip times include up to one polling interval (`-i`) of waiting on each side.

## Next steps

- [x] Alternative versions for the rubric's comparison (3 base station, 2 node), benchmark script
- [ ] Rerun the version benchmark on CAAS or a laptop for the slides
- [ ] Task 3 sweep script: 30+ grid sizes and 30+ line lengths, CSV output, graphs
- [ ] CAAS job scripts
- [ ] Test different `-w` window values (spec requirement)
