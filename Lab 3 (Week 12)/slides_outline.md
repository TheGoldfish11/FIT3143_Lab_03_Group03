# Lab 3 slides: outline

Julia Mallard, Nam Quang Tran - FIT3143 Lab 03, Group 03

About 14 content slides for 7 minutes, so roughly 25-30 s each. Aim for Task 1 ≈ 2 min,
Task 2 + versions ≈ 2 min, Task 3 ≈ 2 min, wrap-up ≈ 1 min. Images are in
`diagrams/png/` and `wsn/results/`. Replace the trial graphs with your laptop/CAAS ones.

---

## 1. FIT3143 Lab 3 | Julia Mallard, Nam Quang Tran
EV charging WSN simulation with Open MPI + OpenMP

## 2. Task 1: EV Charging Nodes  *(section slide)*

## 3. System architecture
*Image: `01-architecture.png`*
- m × n nodes + 1 base station = m·n + 1 MPI processes
- Nodes on an MPI Cartesian topology (`MPI_Cart_create`, non-periodic)
- 2–4 neighbours each, from `MPI_Cart_shift`
- Every node reaches the base station directly

## 4. Inside a charging node
*Image: `02-node-internals.png`*
- One MPI process, k + 1 OpenMP threads
- Port threads: each cycle a port fills (p = 0.6) or frees (p = 0.3)
- Shared array `port_in_use[k]`: each thread writes only its own slot (atomic)
- Thread 0: the only MPI thread (`MPI_THREAD_FUNNELED`), logs availability like Table 1

## 5. Handling congestion
*Image: `03-node-flow.png`*
- Free ports ≤ threshold → `NBR_REQ` to every neighbour
- A neighbour has space → redirect EVs, no base station message
- All neighbours full → one `REPORT` → forward the base station's reply to EVs
- Sample run: 66 of 72 incidents solved by neighbours

## 6. Message passing
*Table (from diagram 6):*

| Message | From → to | Size |
|---|---|---|
| `NBR_REQ` / `NBR_RESP` | node ⇄ neighbour | 12 B / 16 B |
| `REPORT` | node → base | 104 B |
| `BASE_REPLY` | base → node | 540 B |
| `TERMINATE` / `TERM_ACK` / `FINAL` | shutdown | 0 / 140 / 0 B |

- Each message is one MPI derived datatype → one call per report
- Report: timestamp, ID, (x, y), own + neighbour free ports, neighbour message count and bytes

## 7. Key code: thread 0's loop
```
while not FINAL:
    while MPI_Iprobe(any source, any tag):     // handle everything that arrived
        MPI_Recv, then react (request / reply / base reply / terminate)
    every cycle:
        free = free slots in port_in_use
        if free <= threshold: MPI_Isend NBR_REQ to each neighbour
    if nothing arrived: sleep one poll interval
```
- Never waits on a reply → no deadlock when neighbours fill up together (appendix A1)

## 8. Task 2: Base Station  *(section slide)*

## 9. Base station and shutdown
*Image: `04-base-station.png` (whole diagram)*
- One MPI process, one thread; logs every alert and a summary
- All of R's neighbours reported within w s → "no nodes available nearby"
- Otherwise search outward from 2 hops → return **all** nodes at the closest distance
- Shutdown: `TERMINATE` → `TERM_ACK` from every node → `FINAL` → nothing left unreceived

## 10. Nearest-node search: real alerts
*Image: `05-nearest-node-example.png`*
- Alert #5: Node 0 → node 2 (nodes 4 and 6 had just reported)
- Alert #6: Node 3 → none nearby (all its neighbours had reported)

## 11. Blocking vs non-blocking versions
*Image: `08-base-station-versions.png`*
- Base station: **poll** (`Iprobe` + sleep), **block** (`Probe`), **irecv** (`Irecv` + `Testany`)
- Nodes: **non-blocking**, **blocking** (still answers requests while waiting)
- Blocking base can't watch the clock → node 0 sends `TIME_UP`

## 12. Versions: results
*Images: `versions_report_rtt.png`, `versions_base_cpu.png`*
- Blocking is fastest: 0.08 ms report round trip vs ~3 ms
- But Open MPI busy-waits: 99% CPU vs ~2.5%
- Default = poll: latency tunable with `-i`, CPU stays free

#### 13. Task 3: Communication Analysis   *(section slide)*

#### 14. Benchmark Methodology & Setup
*  **Single-Clock Round Trips**: Timed on node/base clock to eliminate clock sync issues (`NBR_REQ` → `NBR_RESP`, `REPORT` → `BASE_REPLY` net of $T_{\text{proc}}$, `TERMINATE` → `TERM_ACK`).
*  **Comprehensive HD Dataset**: Benchmark suite executed across **60 distinct topologies** (30 2D grids from 2×2 to 8×8, 30 1D lines from 1×2 to 1×31, 180 total runs) on the **CAAS cluster**.
*  **Low Polling Floor**: Configured `POLL_US=100` (100 µs polling interval) so idle wait overhead stays $\le 50\,\mu\text{s}$, isolating true network transport scaling.

#### 15. Delay vs Grid Size & Line Length (Q3a & Q3b)
*Images: task3_grid_scaling.png, task3_line_scaling.png, task3_grid_vs_line.png*
*  **Question 3a (2D Grid Scaling)**:
   * Neighbour RTT stays strictly $O(1)$ constant at $\approx 0.35\,\text{ms}$ ($0\,\mu\text{s/node}$).
   * Base Report RTT scales **sub-linearly** $O(\sqrt{N})$ at **$37\,\mu\text{s/node}$**, expanding mildly from $0.72\,\text{ms}$ ($2\times 2$) to $1.92\,\text{ms}$ ($5\times 6$, $N=30$).
*  **Question 3b (1D Line Topology Scaling)**:
   * Base Report RTT scales **strictly linearly** $O(N)$ at **$220\,\mu\text{s/node}$**—growing **5.9x faster per node** due to $O(N)$ linear network diameter ($D=N$).
   * At $N=30$ nodes, Base Report RTT reaches **$7.02\,\text{ms}$ in a Line** vs **$1.92\,\text{ms}$ in a 2D Grid** (**3.7x higher latency**).

#### 16. Topology Performance Comparison
*Table: Summary Comparison (CAAS Cluster Runs)*
| Metric | 2D Grid Topology ($O(\sqrt{N})$) | 1D Line Topology ($O(N)$) | Growth Ratio |
| :--- | :--- | :--- | :--- |
| **Neighbour RTT** | $0.35\,\text{ms}$ ($O(1)$ flat) | $0.35\,\text{ms}$ ($O(1)$ flat) | Identical 1-hop local exchange |
| **Base Report RTT (N=30)** | $1.92\,\text{ms}$ ($37\,\mu\text{s/node}$) | $7.02\,\text{ms}$ ($220\,\mu\text{s/node}$) | **Line is 3.7x slower at N=30** |
| **Shutdown RTT** | Linear $O(N)$ ($140\,\mu\text{s/node}$) | Linear $O(N)$ ($150\,\mu\text{s/node}$) | Base Station sequential ACK processing |

*  **Key takeaway**: 2D Cartesian topology prevents network congestion and hop-count explosion, keeping latency sub-linear as the network scales.

#### 17. Issues, Limitations & Future Work
*  **CPU Oversubscription**: Laptop testing inflates latency due to thread contention; cluster execution (CAAS) provides clean physical network latency.
*  **Single Base Station Bottleneck**: Central coordinator becomes a processing bottleneck as $N > 100$ $\rightarrow$ implement multi-region base stations.
*  **State Freshness**: Base station relies on periodic report snapshots; rapid EV arrivals can result in stale candidate nodes.
*  **Future Work**: persistent non-blocking communication (`MPI_Recv_init`), hybrid OpenMP dynamic thread scheduling, and real-world EV arrival trace integration.

#### 18. Q&A
Any questions?

---

## Appendix  *(label these clearly)*
- **A1. Why non-blocking**: `07-blocking-vs-nonblocking.png`
- **A2. Message sequence and delay timing**: `06-message-sequence.png`
- **A3. Changes since Applied 1**: the table at the end of the diagrams page
