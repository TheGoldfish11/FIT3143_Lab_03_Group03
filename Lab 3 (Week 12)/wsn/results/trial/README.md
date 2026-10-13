# Trial run of the version benchmark

Made with `bench/bench_versions.sh` (4x4 grid, 15 s runs, cycle 500 ms, poll interval 1000 us,
3 repeats) on a 4-core cloud container. That is 17 MPI processes and about 100 threads on 4
cores, so the machine was heavily oversubscribed. Use these numbers to see the pattern only;
rerun on CAAS or a laptop for the slides.

- `versions.csv`: one row per run, written by the program's `-C` option
- `versions_summary.csv`: mean per version, written by `bench/plot_versions.py`
- `versions_*.png`: the graphs

The blocking base station with non-blocking nodes has a large spread because one report in
the first run took 575 ms. The base station was spinning on a core the oversubscribed nodes
needed. The other two runs of that version averaged 2.6 ms and 2.2 ms.
