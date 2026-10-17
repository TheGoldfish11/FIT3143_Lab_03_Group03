# Task 3 handover (for Julia)

From Nam. Task 3 is yours: run the experiments, read the results, answer the two questions and
make the Task 3 slides. The tools are ready and tested; **no Task 3 results exist yet**.

## What you need from Nam

Nothing needs sending. Everything is on the branch `claude/bold-pascal-zwzuas`:

```sh
git pull origin claude/bold-pascal-zwzuas
```

Please check you have:
- [ ] **Edit access to the slide deck** (the Google Slides file, "FIT3143 Lab 3"). Add your slides after the "Task 3" section slide, in the same style.
- [ ] **A way to run MPI:** a Mac/Linux laptop with Open MPI, a Linux container, or your CAAS login (needs the Monash VPN with GlobalProtect; Nam couldn't connect because of its device health check).
- [ ] **Your own prompt records** if you used an AI tool. The spec wants an AI declaration and the prompts as PDFs. Tell Nam what you used so both go in the declaration.

## What Task 3 asks

- Measure the delay of **each message type**.
- a) How does delay scale as the **grid** gets bigger?
- b) How does delay scale as a **line** (1 × N) gets longer?
- Graphs for both. The rubric wants **30+ grid sizes and 30+ line lengths** for HD (20+ for D),
  with CAAS used extensively for D/HD.

## What's ready

All in `Lab 3 (Week 12)/wsn/`. The README's "Task 3 sweep" and "Running on CAAS" sections have details.

| Piece | What it does |
|---|---|
| `./wsn ... -C file.csv` | each run appends one CSV row with every measurement |
| `bench/configs.sh` | the 30 grid sizes (2×2 → 5×6), 30 lines (1×2 → 1×31) and run settings |
| `bench/sweep_task3.sh` | runs them all on a laptop or container (3 repeats ≈ 35 min) |
| `bench/plot_task3.py` | 3 graphs (grids, lines, grid vs line) + `task3_summary.csv` + growth per node |
| `caas/submit_task3.sh` | same sweep on CAAS, one job per size (CAAS: 32 processes, 10 min per job) |

Three round trips are timed per run:

| Pair | Timed by | Note |
|---|---|---|
| `NBR_REQ → NBR_RESP` | the asking node | only neighbours involved |
| `REPORT → BASE_REPLY` | the reporting node | base station's processing time is subtracted |
| `TERMINATE → TERM_ACK` | the base station | once per node at shutdown |

## Steps

1. Build: `cd "Lab 3 (Week 12)/wsn" && make`.
   - Mac: `brew install open-mpi libomp` first. **The Mac build has not been tested.**
   - Nam ran everything in a Linux container: `docker run -it --rm --shm-size=1g -v "$PWD":/work ...`.
     `--shm-size=1g` matters, because Docker's 64 MB default can make MPI runs hang.
     Python needs `python3 python3-matplotlib python3-numpy` (apt).
2. Quick check (1 minute): `WHICH=lines REPEATS=1 DURATION=3 bench/sweep_task3.sh`, then
   `python3 bench/plot_task3.py results/task3`. Delete `results/task3` afterwards.
3. Full run: `bench/sweep_task3.sh`, and/or `caas/submit_task3.sh` on CAAS.
4. Plot with `python3 bench/plot_task3.py results/task3` and read the slopes it prints.
5. Answer a) and b) from the graphs, and make the slides.
6. Commit the `results/task3` folder and push, so everyone has it.

**Put options on the same line as the command**, for example `WHICH=lines REPEATS=1 bench/sweep_task3.sh`.
Typed on their own line, they don't apply and the script uses its defaults.

## Slides to make

After the "Task 3" section slide, about three slides (the deck's time budget is tight, so keep
each to 3 bullets):

1. **Method:** round trips on one clock (no clock sync needed), 30 grid sizes and 30 lines, repeats,
   poll interval 100 µs, where it ran (container or CAAS, and its core count).
2. **Delay vs grid size and line length:** `task3_grid_vs_line.png` plus 2-3 bullets answering a) and b).
3. **Window test (`-w`):** optional for you; Nam may take it. Run `bench/sweep_window.sh`, then
   `python3 bench/plot_window.py results/window`.

Also add a line for the Task 3 limitations to the final limitations slide.

## Things to know before you interpret

- **These are round trips.** One-way delay ≈ half. Round trips avoid needing synchronised clocks.
- **Polling adds a floor.** Each side waits up to one poll interval. The sweep uses 100 µs
  (`POLL_US`); the default 1000 µs would hide most of the effect. In Nam's version benchmark
  (1000 µs), non-blocking round trips were about 7-8 ms, mostly waiting, not network.
- **Oversubscription matters.** A laptop or container runs up to 32 processes × 7 threads on a few
  cores, so CPU contention grows with size. That is a real result, but say it's CPU, not network.
  On CAAS, `TASKS_PER_NODE=4` spreads jobs over more machines, so more messages cross the network.
- **Same seed ≠ same run.** Thread timing changes which ports flip, so use the repeats (whiskers).
- **Applied 1 predicted** neighbour messages stay O(1) and node → base messages are O(1) with a
  direct link. Check whether the measurements agree, and explain any growth.
- **Orientation check:** the grid list includes 2×3 and 3×2 (and 3×4 and 4×3), so you can show
  that only the node count matters, not the shape.

## Already done (for context)

- Version benchmark (3 base station × 2 node versions, 4×4 grid, 3 repeats): `results/versions*`.
  Blocking is fastest (0.02 ms report round trip) but uses 100% of a core; polling uses under 0.5%.
- Slides for Tasks 1 and 2 are in the deck; the outline is `slides_outline.md`.

## Q&A you should be ready for

- Why round trips, not one-way delay?
- Why does (or doesn't) each delay grow with size?
- What's different on a line vs a grid with the same number of nodes?
- How would results change on CAAS vs a laptop?
- What does the polling interval do to your numbers?
