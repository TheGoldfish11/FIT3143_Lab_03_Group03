# Task 3 handover (for Julia)

From Nam. Task 3 is yours: running the experiments, reading the results, answering the two
questions and making slides 14-16. The tools are ready; no Task 3 results have been collected yet.

## What Task 3 asks

- Measure the delay of **each message type**.
- a) How does delay scale as the **grid** gets bigger?
- b) How does delay scale as a **line** (1 × N) gets longer?
- Graphs for both. The rubric wants **30+ grid sizes and 30+ line lengths** for HD (20+ for D),
  with CAAS used extensively for D/HD.

## What's ready

All in `wsn/`. See the README's "Task 3 sweep" and "Running on CAAS" sections for details.

| Piece | What it does |
|---|---|
| `./wsn ... -C file.csv` | each run appends one CSV row with every measurement |
| `bench/configs.sh` | the 30 grid sizes (2×2 → 5×6), 30 lines (1×2 → 1×31) and run settings |
| `bench/sweep_task3.sh` | runs them all on a laptop (3 repeats ≈ 35 min) |
| `bench/plot_task3.py` | 3 graphs (grids, lines, grid vs line) + `task3_summary.csv` + growth per node |
| `caas/submit_task3.sh` | same sweep on CAAS, one job per size (CAAS: 32 processes, 10 min per job) |

Three round trips are timed per run:

| Pair | Timed by | Note |
|---|---|---|
| `NBR_REQ → NBR_RESP` | the asking node | only neighbours involved |
| `REPORT → BASE_REPLY` | the reporting node | base station's processing time is subtracted |
| `TERMINATE → TERM_ACK` | the base station | once per node at shutdown |

Tested on Linux and with stand-in SLURM commands. **Not yet run on a Mac or on real CAAS.**

## Steps

1. `cd "Lab 3 (Week 12)/wsn" && make` (Mac: `brew install open-mpi libomp` first).
2. Quick check: `WHICH=lines REPEATS=1 DURATION=3 bench/sweep_task3.sh`, then
   `python3 bench/plot_task3.py results/task3`. Delete `results/task3` afterwards.
3. Full run: `bench/sweep_task3.sh` on a laptop, and/or `caas/submit_task3.sh` on CAAS.
4. Plot, then answer a) and b) from the graphs and the printed slopes.
5. Fill in slides 14-16 in `slides_outline.md`.

## Things to know before you interpret

- **These are round trips.** One-way delay ≈ half. Round trips avoid needing synchronised clocks.
- **Polling adds a floor.** Each side waits up to one poll interval. The sweep uses 100 µs
  (`POLL_US`); the default 1000 µs would hide most of the effect.
- **Oversubscription matters.** A laptop runs up to 32 processes × 7 threads on a few cores, so
  CPU contention grows with size. That is a real result, but say it's CPU, not network.
  On CAAS, `TASKS_PER_NODE=4` spreads jobs over more machines, so more messages cross the network.
- **Same seed ≠ same run.** Thread timing changes which ports flip, so use the repeats (whiskers).
- **Applied 1 predicted** neighbour messages stay O(1) and node → base messages are O(1) with a
  direct link. Check whether the measurements agree, and explain any growth.

## Q&A you should be ready for

- Why round trips, not one-way delay?
- Why does (or doesn't) each delay grow with size?
- What's different on a line vs a grid with the same number of nodes?
- How would results change on CAAS vs a laptop?
