# Lab 3 slide diagrams

Julia Mallard, Nam Quang Tran - FIT3143 Lab 03, Group 03

Diagrams of the `wsn/` simulation for the Task 4 slides. `png/` has 2560 x 1440 images to drop
into slides. `svg/` has the same diagrams as vector files (PowerPoint, Keynote and Google Slides
can insert SVG directly).

| File | Slide section | Shows |
|---|---|---|
| `01-architecture` | Tasks 1 + 2 | MPI processes, Cartesian grid, base station, message links |
| `02-node-internals` | Task 1 (required diagram) | one node: port threads, shared `port_in_use[]`, thread 0, history |
| `03-node-flow` | Task 1 | thread 0's polling loop and how a congestion incident is handled |
| `04-base-station` | Task 2 (required diagram) | base station loop, `handle_report` decision, two-phase shutdown |
| `05-nearest-node-example` | Task 2 | alerts #5 and #6 from `wsn/sample_logs/base_station_3x3.log` |
| `06-message-sequence` | Tasks 1-3 | every message type with its size, and how delay is timed |
| `07-blocking-vs-nonblocking` | Task 1 / Q&A | why blocking receives deadlock and the polling loop does not |

Colours mean the same thing in every diagram: blue = nodes and node-to-node messages,
amber = base station and node-to-base messages, green = ports or a good outcome,
red = congested, grey = shutdown messages, ruled out, notes.

## Regenerating

The SVGs are generated so they stay consistent. To change a label, edit `make_diagrams.py` and run

```sh
python3 make_diagrams.py
```

The PNGs were rendered from the SVGs with headless Chromium at 2x scale, using the Public Sans and
JetBrains Mono fonts. Opening an SVG in a browser and taking a screenshot works too.
