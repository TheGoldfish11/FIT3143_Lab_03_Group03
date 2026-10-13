# FIT3143 Lab 3 - experiment settings shared by the laptop scripts (bench/) and CAAS jobs (caas/)
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# Sourced, not run. Every value can be overridden with an environment variable of the same name.
# Written for bash 3.2 too (the macOS default).

# Task 3a: 30 grid sizes (rows x cols). CAAS allows 32 MPI processes per job, so the biggest
# grid is 31 nodes + the base station. 3x2 and 4x3 repeat 2x3 and 3x4 turned on their side,
# as a check that only the size matters, not the orientation.
GRIDS=${GRIDS:-"2x2 2x3 3x2 2x4 3x3 2x5 2x6 3x4 4x3 2x7 3x5 2x8 4x4 2x9 3x6 2x10 4x5 3x7 2x11 2x12 3x8 4x6 5x5 2x13 3x9 2x14 4x7 2x15 3x10 5x6"}

# Task 3b: 30 line topologies, 1x2 to 1x31
LINES=${LINES:-"$(for i in $(seq 2 31); do printf '1x%s ' "$i"; done)"}

# window values (seconds) for the base station's "recent report" rule
WINDOWS=${WINDOWS:-"0 0.5 1 2 3 5 8 12 20"}

# run settings: a busy grid so every run has plenty of reports to time
DURATION=${DURATION:-10}
CYCLE_MS=${CYCLE_MS:-500}
P_ARRIVE=${P_ARRIVE:-0.8}
P_DEPART=${P_DEPART:-0.2}
POLL_US=${POLL_US:-100}         # short poll interval, so polling adds little to the measured delay
REPEATS=${REPEATS:-3}
BASE=${BASE:-poll}
NODE=${NODE:-nonblock}
