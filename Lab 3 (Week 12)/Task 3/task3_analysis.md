# Task 3 Communication Analysis

Julia Mallard, Nam Quang Tran - FIT3143 Lab 03, Group 03

## Executive Summary
This document provides a comprehensive empirical and theoretical analysis of inter-process communication latency in a distributed Wireless Sensor Network (WSN) simulating Electric Vehicle (EV) charging grid congestion. Benchmarks were conducted across **60 distinct network topologies** (30 2D Cartesian grids and 30 1D line topologies, tested over 180 total runs) with a $100\,\mu\text{s}$ polling interval on the CAAS computing cluster.

---

## 1. Quantitative Performance Summary

| Metric | Message Pair | 2D Grid Scaling | 1D Line Scaling | Growth Comparison |
| :--- | :--- | :--- | :--- | :--- |
| **Neighbour RTT** | `NBR_REQ` $\rightarrow$ `NBR_RESP` | $O(1)$ Constant ($\approx 0.35\,\text{ms}$) | $O(1)$ Constant ($\approx 0.35\,\text{ms}$) | Identical 1-hop local exchange ($0\,\mu\text{s/node}$) |
| **Base Report RTT** | `REPORT` $\rightarrow$ `BASE_REPLY` | $O(\sqrt{N})$ Sub-linear ($37\,\mu\text{s/node}$) | $O(N)$ Linear ($220\,\mu\text{s/node}$) | Line latency grows **5.9x faster per node** |
| **Shutdown RTT** | `TERMINATE` $\rightarrow$ `TERM_ACK` | $O(N)$ Linear ($140\,\mu\text{s/node}$) | $O(N)$ Linear ($150\,\mu\text{s/node}$) | Base station sequential ACK processing |

---

## 2. Question 3a: 2D Cartesian Grid Topology Scaling Analysis

### **Key Empirical Finding**
In a 2D Cartesian grid topology ($m \times n$), Base Station Report RTT scales **sub-linearly** with process count $N$, increasing at an empirical rate of **$37\,\mu\text{s}$ per node**. As the grid expands from $2\times 2$ ($N=4$) to $8\times 8$ ($N=64$), round-trip latency increases mildly from $0.72\,\text{ms}$ to $3.03\,\text{ms}$.

### **Technical Drivers & Physics**
1. **Cartesian Network Diameter $O(\sqrt{N})$**:
   In a 2D grid, the spatial distance between the furthest node $(0,0)$ and the Base Station scales with grid dimensions $D = (m-1) + (n-1) \approx O(\sqrt{N})$. The compact two-dimensional structure keeps message hop counts significantly lower than in elongated topologies.
2. **Local Neighbour Independence $O(1)$**:
   Neighbour queries (`NBR_REQ` $\rightarrow$ `NBR_RESP`) execute purely between 1-hop Cartesian adjacent ranks via `MPI_Cart_shift`. Because messages do not travel through intermediate nodes, neighbour exchange delay remains flat at $\approx 0.35\,\text{ms}$ regardless of total grid size $N$.
3. **100 $\mu\text{s}$ Polling Interval Overhead**:
   Reducing the `MPI_Iprobe` polling interval from $1000\,\mu\text{s}$ to $100\,\mu\text{s}$ ensures idle polling wait time adds a negligible floor of $\le 50\,\mu\text{s}$ per hop, preventing polling artifacts from masking true network transport scaling.
4. **Subtracted Base Processing Time ($T_{\text{proc}}$)**:
   The Base Station's candidate-search execution duration ($T_{\text{proc}}$) is subtracted from `BASE_REPLY` timestamps before logging, ensuring the measured metric reflects pure network transmission and queueing delay.

---

## 3. Question 3b: 1D Line Topology Scaling Analysis

### **Key Empirical Finding**
In a 1D line topology ($1 \times N$), Base Station Report RTT scales **strictly linearly $O(N)$** with process count $N$, escalating at an empirical rate of **$220\,\mu\text{s}$ per node**. At $N=30$ nodes, Base Station Report RTT reaches **$7.02\,\text{ms}$ in a Line** compared to **$1.92\,\text{ms}$ in a 2D Grid**—representing a **3.7x latency penalty** caused entirely by spatial layout.

### **Technical Drivers & Physics**
1. **Linear Hop Count Escalation $O(N)$**:
   In a 1D line ($1 \times N$), the Base Station resides at process $N$, and node 0 is $N$ hops away ($D = N$). Every message sent from distant nodes must traverse $N$ intermediate links, creating a cumulative hop delay that grows linearly with scale.
2. **Spatial Routing Bottlenecks**:
   Unlike 2D Cartesian grids which offer multiple alternative spatial pathways, 1D line topologies constrain all communication to a single linear backbone. This causes cumulative store-and-forward delays and message queueing at intermediate processes.

---

## 4. Key Takeaways for WSN System Architecture
* **Topology Choice**: 2D Cartesian grid layouts are dramatically superior for distributed sensor grids, suppressing network latency by up to **73%** at 30 nodes compared to line topologies.
* **Granular Messaging**: Local neighbour interactions scale perfectly at $O(1)$, proving that local EV redirection eliminates unnecessary centralized base station traffic when neighbouring ports are free.