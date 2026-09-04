# Task 3 — Communication (Delay) Analysis

## 1. Delay model and assumptions

We use the standard **Hockney (latency-bandwidth) model** for point-to-point transmission delay:

```
T(S) = t_startup + S / BW
```

- `t_startup` — fixed per-message overhead (network + MPI software latency), assumed **20 microseconds**
  (typical order of magnitude for MPI point-to-point communication over Gigabit Ethernet/TCP).
- `S` — message payload size, in **bits**.
- `BW` — link bandwidth, **1 Gbps = 1×10⁹ bits/sec** (per the Task 3 assumption).

Message payload sizes are derived directly from the fields defined on the Task 2 sequence
diagram ("MPI Communication Between Simulation Components"), using these per-field size
assumptions:

| Field type | Size |
|---|---|
| `int` (IDs, port counts) | 4 bytes |
| `double` (utilisation ratios, coordinate components) | 8 bytes |
| `coordinates` (x, y) | 2 × double = 16 bytes |
| `neighbourStatusSummary` | up to 4 × double = 32 bytes (worst case: interior node, 4 neighbours) |

## 2. Message size and delay table

| Message | Fields | Size (bytes) | Delay (µs) | Bandwidth-term share of delay |
|---|---|---:|---:|---:|
| `STATUS_UPDATE` | nodeID, coordinates, freePorts, usedPorts, utilisation | 36 | 20.288 | 1.42% |
| `NEIGHBOUR_STATUS_REQUEST` | originID | 4 | 20.032 | 0.16% |
| `NEIGHBOUR_STATUS_RESPONSE` | nodeID, freePorts, utilisation | 16 | 20.128 | 0.64% |
| `CONGESTION_ALERT` | originNodeID, coordinates, originUtilisation, neighbourStatusSummary | 60 | 20.480 | 2.34% |
| `REDIRECT` | targetNodeID, targetCoordinates, availablePorts | 24 | 20.192 | 0.95% |

**Key theoretical conclusion**: for every message type, the bandwidth term (`S/BW`) contributes
under 2.5% of total transmission delay. All five message types are **latency-bound, not
bandwidth-bound** — the 1 Gbps link is never close to being the limiting factor for an
individual message, because these are small, fixed-size control/status payloads, not bulk data
transfers.

## 3. Connectivity assumption (this changes the answer to 3a/3b, so it is stated explicitly)

Rather than assuming every ChargingNode has its own direct link to the BaseStation, this
analysis assumes the more physically realistic **single-radio WSN** case: only **one**
ChargingNode (a corner of the k×k mesh) has an actual direct link to the BaseStation. Every
other node must **relay its ChargingNode↔BaseStation messages hop-by-hop through the 2D mesh**
to reach that one connected node, the same way real WSNs typically route to a sink node when
individual sensors don't have a long-range radio. Each hop is modelled as a full
store-and-forward step, paying the complete Hockney delay again (`hops × transmission_delay`).
Neighbour-to-neighbour messages are unaffected by this assumption — they are always exactly
one hop regardless of how (or whether) the network reaches a base station.

## 4. Task 3(a) — Scaling with number of charging nodes (N)

*See `graph_delay_vs_nodes.png`.*

- **`NEIGHBOUR_STATUS_REQUEST` / `NEIGHBOUR_STATUS_RESPONSE` — O(1), independent of N.**
  These only ever travel to/from a node's immediate mesh neighbours (bounded at 2–4 by the
  2D mesh topology), never scaling with total network size. This is the direct communication
  payoff of choosing a 2D mesh over a completely-connected topology in Task 1.

- **`STATUS_UPDATE`, `CONGESTION_ALERT`, `REDIRECT` — O(√N), driven by worst-case relay
  distance.** Under the single-gateway assumption, a node's message may need to be relayed
  through several intermediate nodes to reach the one node connected to the BaseStation. For
  a k×k mesh (N = k²), the worst case is the Manhattan distance from the opposite corner:
  `2(k − 1)` hops — which grows as `2(√N − 1)`, i.e. **O(√N)**. At N=100 this is 18 hops,
  giving roughly 365 µs worst-case delay for `STATUS_UPDATE` — an 18× increase over the
  single-hop 20.288 µs figure, purely from relay distance.

**Conclusion for 3(a)**: neighbour messages remain flat regardless of network size, because
the mesh bounds neighbour count independent of N. Node↔BaseStation messages, however, scale
as O(√N) once a single-gateway (rather than direct-link-per-node) connectivity assumption is
used — the worst-case relay distance across the mesh grows with the mesh's own diameter.

## 5. Task 3(b) — Effect of increasing the number of base stations (B)

*See `graph_delay_vs_base_stations.png`, N held fixed at 81 (9×9 mesh) for illustration.*

Increasing B now means distributing B gateway nodes evenly across the same mesh, rather than
relying on one corner. This is a standard coverage-geometry result: spreading B points evenly
over a fixed area shrinks the region each one serves proportionally to 1/B, so the maximum
distance from any point in that region to its nearest gateway shrinks proportionally to
**1/√B**. Concretely, at N=81 (worst case 16 hops with B=1), doubling to B=2 gateways drops
the worst-case relay distance to ~11 hops (~229 µs); by B=8 it falls to ~6 hops (~115 µs).

- **Neighbour messages are completely unaffected by B** — still O(1), since they never
  route toward a base station at all.
- **Node↔BaseStation messages improve as O(1/√B)** — genuinely reducing worst-case
  *transmission* delay, not just aggregate contention, since fewer relay hops are needed to
  reach the nearest gateway.

**Conclusion for 3(b)**: increasing the number of base stations **does reduce transmission
delay** for node↔BaseStation messages, because it shortens the physical relay distance any
node needs to traverse to reach one — this is also why real deployments (cell towers, WSN
sinks) add more base stations as coverage area grows: it is a physical reachability
improvement, not only a load-balancing one. This complements the physical-feasibility point
raised earlier in discussion: beyond a certain deployment size, additional base stations are
not just a performance optimisation but become necessary for any node to reach one within
its radio's practical range.

## 6. Bonus: delay vs. other growing factors (message frequency)

*See `graph_delay_vs_frequency.png`.*

Beyond N and B, the spec's own bandwidth formula (`BW ≈ N × d × f × S`) identifies message
frequency `f` as a scaling factor — driven in practice by a growing number of EVs or higher
charging turnover. Modelling the BaseStation's inbound link as a simple M/M/1 queue
(`D = service_time / (1 − utilisation)`), delay stays close to the fixed ~20 µs baseline
until the arrival rate approaches the link's saturation point (~49,290 messages/sec at this
message size and bandwidth), after which delay grows sharply — a classic queueing
blow-up. This shows that while any single message stays latency-bound in isolation, a
sufficiently large or fast-charging deployment could still push the BaseStation's inbound
link toward saturation, independent of how many charging nodes or base stations exist.
