"""
Task 3 - Communication (delay) analysis for the EVCNS WSN simulation.

Model: Hockney (latency-bandwidth) model
    T(S) = t_startup + S / BW
where:
    t_startup = fixed per-message overhead (network + MPI software latency)
    S         = message payload size, in bits
    BW        = link bandwidth (1 Gbps, per spec)

Message payload sizes are estimated from the field lists on the Task 2
"MPI Communication Between Simulation Components" sequence diagram.
Field size assumptions (documented so they can be defended in Q&A):
    int     -> 4 bytes   (nodeID, originID, targetNodeID, freePorts, usedPorts, availablePorts)
    double  -> 8 bytes   (utilisation ratios, coordinate components)
    coordinates -> 2 x double (x, y)              = 16 bytes
    neighbourStatusSummary -> up to 4 x double     = 32 bytes (worst case: interior node, 4 neighbours)
"""

import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BW_BPS = 1e9                # 1 Gbps link, per Task 3 assumption
T_STARTUP_S = 20e-6          # 20 microseconds: typical MPI-over-Ethernet startup latency

INT = 4
DOUBLE = 8
COORD = 2 * DOUBLE           # (x, y) as doubles

# ---------------------------------------------------------------------------
# Message payload sizes (bytes), derived from Task 2's sequence diagram fields
# ---------------------------------------------------------------------------
MESSAGES = {
    "STATUS_UPDATE": {
        "fields": "nodeID + coordinates + freePorts + usedPorts + utilisation",
        "size_bytes": INT + COORD + INT + INT + DOUBLE,          # 4+16+4+4+8 = 36
        "sender": "ChargingNode", "receiver": "BaseStation",
    },
    "NEIGHBOUR_STATUS_REQUEST": {
        "fields": "originID",
        "size_bytes": INT,                                        # 4
        "sender": "ChargingNode", "receiver": "Neighbour (2-4)",
    },
    "NEIGHBOUR_STATUS_RESPONSE": {
        "fields": "nodeID + freePorts + utilisation",
        "size_bytes": INT + INT + DOUBLE,                         # 16
        "sender": "Neighbour", "receiver": "Origin ChargingNode",
    },
    "CONGESTION_ALERT": {
        "fields": "originNodeID + coordinates + originUtilisation + neighbourStatusSummary(<=4)",
        "size_bytes": INT + COORD + DOUBLE + 4 * DOUBLE,          # 4+16+8+32 = 60 (worst case)
        "sender": "ChargingNode", "receiver": "BaseStation",
    },
    "REDIRECT": {
        "fields": "targetNodeID + targetCoordinates + availablePorts",
        "size_bytes": INT + COORD + INT,                          # 24
        "sender": "BaseStation", "receiver": "ChargingNode",
    },
}


def transmission_delay(size_bytes: float) -> float:
    """Hockney model: T = t_startup + S(bits) / BW"""
    return T_STARTUP_S + (size_bytes * 8) / BW_BPS


def multihop_delay(size_bytes: float, hops: float) -> float:
    """
    Store-and-forward relay: each hop is a fresh receive+resend, so each hop
    pays the full per-message Hockney cost again.
    Only ChargingNode<->BaseStation messages are affected by this -- neighbour
    messages are always exactly 1 hop regardless of base-station connectivity.
    """
    return hops * transmission_delay(size_bytes)


def worst_case_hops_single_gateway(N):
    """
    Only ONE node (a corner of the k x k mesh) has a direct link to the
    BaseStation; every other node must relay hop-by-hop through the mesh to
    reach it. Worst case = Manhattan distance from the opposite corner:
    (k-1) + (k-1) = 2(k-1), for a k x k mesh (N = k^2).
    """
    k = np.sqrt(N)
    return 2 * (k - 1)


def worst_case_hops_multi_gateway(N_fixed, B):
    """
    B gateways (base stations), evenly distributed across the same k x k mesh.
    Standard coverage-geometry result: spreading B points evenly over a fixed
    area reduces the maximum distance to the nearest point by a factor of
    sqrt(B) (area per gateway shrinks as 1/B, so the region's linear size --
    and therefore worst-case hop distance -- shrinks as 1/sqrt(B)).
    Consistent with worst_case_hops_single_gateway at B=1.
    """
    return worst_case_hops_single_gateway(N_fixed) / np.sqrt(B)


def print_message_table():
    print(f"{'Message':28s} {'Size (B)':>9s} {'Delay (us)':>12s}  Bandwidth-term share")
    for name, m in MESSAGES.items():
        d = transmission_delay(m["size_bytes"])
        bw_term = (m["size_bytes"] * 8) / BW_BPS
        share = bw_term / d * 100
        print(f"{name:28s} {m['size_bytes']:9d} {d*1e6:12.4f}  {share:6.3f}%")


# ---------------------------------------------------------------------------
# Graph A: transmission delay vs number of charging nodes (N)
#
# Assumption: only ONE ChargingNode (a corner of the mesh) has a direct link
# to the BaseStation -- every other node must relay its ChargingNode<->
# BaseStation messages hop-by-hop through the 2D mesh to reach it.
# Neighbour messages are unaffected (always exactly 1 hop, regardless of
# base-station connectivity).
# ---------------------------------------------------------------------------
def graph_delay_vs_nodes(out_path):
    # 2D mesh grid sizes: k x k for k = 2..10  ->  N = 4, 9, 16, ..., 100
    k = np.arange(2, 11)
    N = k ** 2
    hops = worst_case_hops_single_gateway(N)

    fig, ax = plt.subplots(figsize=(9, 6))

    # Neighbour messages: always exactly 1 hop to an immediate neighbour,
    # regardless of network size or base-station connectivity -- O(1)
    for name in ["NEIGHBOUR_STATUS_REQUEST", "NEIGHBOUR_STATUS_RESPONSE"]:
        d_us = transmission_delay(MESSAGES[name]["size_bytes"]) * 1e6
        ax.plot(N, np.full_like(N, d_us, dtype=float), marker='o', linewidth=1.5,
                label=f"{name}  (O(1), always 1 hop)")

    # ChargingNode <-> BaseStation messages: must relay through the mesh to
    # reach the single connected node -- worst-case delay scales with the
    # mesh's diameter, O(sqrt(N))
    for name in ["STATUS_UPDATE", "CONGESTION_ALERT", "REDIRECT"]:
        d_us = multihop_delay(MESSAGES[name]["size_bytes"], hops) * 1e6
        ax.plot(N, d_us, marker='s', linewidth=2, linestyle='--',
                label=f"{name}  (O(sqrt(N)), worst-case relay hops)")

    ax.set_xlabel("Number of charging nodes, N  (k x k mesh)")
    ax.set_ylabel("Transmission delay (microseconds)")
    ax.set_title("Task 3(a): Transmission delay vs. number of charging nodes\n"
                  "REAL-WORLD interpretation: single gateway node connected to the BaseStation")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc='upper left')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Graph: proportion of latency (t_startup) vs payload transmission time,
# per message type -- 100% stacked bar chart
# ---------------------------------------------------------------------------
def graph_latency_vs_payload_proportion(out_path):
    names = list(MESSAGES.keys())
    latency_pct = []
    payload_pct = []

    for name in names:
        size = MESSAGES[name]["size_bytes"]
        total = transmission_delay(size)
        payload_term = (size * 8) / BW_BPS
        latency_term = total - payload_term
        latency_pct.append(latency_term / total * 100)
        payload_pct.append(payload_term / total * 100)

    fig, ax = plt.subplots(figsize=(9, 6))
    x = np.arange(len(names))

    bars_latency = ax.bar(x, latency_pct, label="Latency", color="tab:blue")
    bars_payload = ax.bar(x, payload_pct, bottom=latency_pct,
                           label="Payload transmission", color="tab:orange")

    # Label the (tiny) payload slice with its exact percentage, since it's
    # too thin to read visually
    for i, pct in enumerate(payload_pct):
        ax.text(x[i], 100 - pct - 3, f"{pct:.2f}%", ha='center', va='top',
                fontsize=9, color='white', fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=20, ha='right')
    ax.set_ylabel("Share of total transmission delay (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Latency vs. payload-transmission share of delay, per message type")
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.32), ncol=2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Graph B: transmission delay vs number of base stations (B), N held fixed
#
# B gateway nodes are now evenly distributed across the same k x k mesh
# (instead of just 1 corner). Every ChargingNode relays hop-by-hop through
# the mesh to reach its NEAREST gateway. More base stations -> shorter
# worst-case relay distance to the nearest one.
# ---------------------------------------------------------------------------
def graph_delay_vs_base_stations(out_path, N_fixed=81):
    B = np.arange(1, 9)
    hops = worst_case_hops_multi_gateway(N_fixed, B)

    fig, ax = plt.subplots(figsize=(9, 6))

    # Neighbour messages: unaffected by base-station count -- always 1 hop
    for name in ["NEIGHBOUR_STATUS_REQUEST", "NEIGHBOUR_STATUS_RESPONSE"]:
        d_us = transmission_delay(MESSAGES[name]["size_bytes"]) * 1e6
        ax.plot(B, np.full_like(B, d_us, dtype=float), marker='o', linewidth=1.5,
                label=f"{name}  (O(1), unaffected by B)")

    # ChargingNode <-> BaseStation messages: worst-case relay distance shrinks
    # as O(1/sqrt(B)) as gateways are spread more densely across the mesh
    for name in ["STATUS_UPDATE", "CONGESTION_ALERT", "REDIRECT"]:
        d_us = multihop_delay(MESSAGES[name]["size_bytes"], hops) * 1e6
        ax.plot(B, d_us, marker='s', linewidth=2, linestyle='--',
                label=f"{name}  (O(1/sqrt(B)) worst-case relay hops)")

    ax.set_xlabel("Number of base stations, B  (evenly distributed gateways)")
    ax.set_ylabel("Transmission delay (microseconds)")
    ax.set_title(f"Task 3(b): Transmission delay vs. number of base stations\n"
                 f"REAL-WORLD interpretation: N={N_fixed} fixed, worst-case relay distance to nearest gateway")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc='upper right')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Graphs A2/B2: the CODE/SIMULATION-ONLY interpretation -- every ChargingNode
# has its own direct MPI link to the BaseStation (MPI_COMM_WORLD guarantees
# any-rank-to-any-rank reachability by default, so this costs nothing extra
# to implement). This is the counterpart to graph_delay_vs_nodes/
# graph_delay_vs_base_stations, which model the more physically realistic
# single-radio WSN case where messages must relay hop-by-hop through the mesh.
# ---------------------------------------------------------------------------
def graph_delay_vs_nodes_direct_link(out_path):
    k = np.arange(2, 11)
    N = k ** 2

    fig, ax = plt.subplots(figsize=(9, 6))

    # Every message type is always exactly 1 hop: neighbour messages travel
    # to an immediate neighbour, and ChargingNode<->BaseStation messages use
    # their own direct link -- MPI guarantees this reachability for free, so
    # network size never enters the calculation.
    for name in MESSAGES:
        d_us = transmission_delay(MESSAGES[name]["size_bytes"]) * 1e6
        ax.plot(N, np.full_like(N, d_us, dtype=float), marker='o', linewidth=1.5,
                label=f"{name}  (O(1), direct link)")

    ax.set_xlabel("Number of charging nodes, N  (k x k mesh)")
    ax.set_ylabel("Transmission delay (microseconds)")
    ax.set_title("Task 3(a): Transmission delay vs. number of charging nodes\n"
                 "CODE/SIMULATION-ONLY interpretation: every node has a direct link to the BaseStation")
    ax.set_ylim(0, 25)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc='center right')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def graph_delay_vs_base_stations_direct_link(out_path, N_fixed=81):
    B = np.arange(1, 9)

    fig, ax = plt.subplots(figsize=(9, 6))

    # Every message type stays at its single-hop delay regardless of B --
    # each node already has a direct link, so adding more base stations
    # changes nothing about transmission delay under this assumption.
    for name in MESSAGES:
        d_us = transmission_delay(MESSAGES[name]["size_bytes"]) * 1e6
        ax.plot(B, np.full_like(B, d_us, dtype=float), marker='o', linewidth=1.5,
                label=f"{name}  (O(1), unaffected by B)")

    ax.set_xlabel("Number of base stations, B")
    ax.set_ylabel("Transmission delay (microseconds)")
    ax.set_title(f"Task 3(b): Transmission delay vs. number of base stations\n"
                 f"CODE/SIMULATION-ONLY interpretation: N={N_fixed} fixed, every node already directly linked")
    ax.set_ylim(0, 25)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc='center right')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Graph C (HD bonus): delay vs. message frequency (growing EV arrivals / charge cycling)
# ---------------------------------------------------------------------------
def graph_delay_vs_frequency(out_path):
    # Simple M/M/1-style queueing delay model at the BaseStation's inbound link:
    #   D(f) = service_time / (1 - utilisation),  utilisation = arrival_rate * service_time
    # This captures the "growing number of EVs / higher charging frequency" HD bonus factor.
    per_msg_us = transmission_delay(MESSAGES["STATUS_UPDATE"]["size_bytes"]) * 1e6
    service_time_s = per_msg_us * 1e-6
    saturation_rate = 1 / service_time_s

    f = np.linspace(1, saturation_rate * 0.995, 400)  # up to 99.5% of link saturation

    utilisation = f * service_time_s
    utilisation = np.clip(utilisation, 0, 0.999)  # cap just under saturation
    queueing_delay_us = (service_time_s / (1 - utilisation)) * 1e6

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(f, queueing_delay_us, linewidth=2.5, color='tab:purple')
    ax.axvline(saturation_rate, color='grey', linestyle=':', linewidth=1.5,
               label=f"Link saturation point (~{saturation_rate:,.0f} msgs/sec)")
    ax.set_xlabel("STATUS_UPDATE arrival rate at BaseStation, f (messages/sec)\n"
                  "(driven by growing number of EVs / higher charging frequency)")
    ax.set_ylabel("Effective delay per message (microseconds, log scale)")
    ax.set_yscale('log')
    ax.set_title("Task 4(c) bonus: Delay vs. message frequency (other growing factor)")
    ax.grid(True, which='both', alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    import os

    for d in ("real_world", "code_only", "supporting"):
        os.makedirs(d, exist_ok=True)

    print_message_table()
    graph_delay_vs_nodes("real_world/graph_delay_vs_nodes.png")
    graph_delay_vs_base_stations("real_world/graph_delay_vs_base_stations.png")
    graph_delay_vs_nodes_direct_link("code_only/graph_delay_vs_nodes_direct_link.png")
    graph_delay_vs_base_stations_direct_link("code_only/graph_delay_vs_base_stations_direct_link.png")
    graph_latency_vs_payload_proportion("supporting/graph_latency_vs_payload_proportion.png")
    graph_delay_vs_frequency("supporting/graph_delay_vs_frequency.png")
    print("\nSaved: real_world/graph_delay_vs_nodes.png, real_world/graph_delay_vs_base_stations.png, "
          "code_only/graph_delay_vs_nodes_direct_link.png, code_only/graph_delay_vs_base_stations_direct_link.png, "
          "supporting/graph_latency_vs_payload_proportion.png, supporting/graph_delay_vs_frequency.png")
