# Task 1 — Parallel Prime Finder: How It Works

A plain-English walkthrough of `task1.c`. No C knowledge needed.

---

## 1. What the program does

Given a number `n`, find every prime number below `n`, using several
processes working at the same time. Write the full sorted list to
`primes_output.txt` and print how long it took.

```
mpirun -np 4 ./task1 1000000
```

means "run this program with 4 processes, and find all primes below 1,000,000".

---

## 2. The one idea you must understand first

**Every process runs the exact same code, from the first line to the last.**

The program is not split into a "manager part" and a "worker part". All 4
processes execute every line. They are told apart by a single number:

| Term | Meaning |
|---|---|
| **rank** | This process's ID number: 0, 1, 2, 3, ... |
| **size** | How many processes there are in total (the `-np` number) |

So when you see code that says "if I am rank 0, print the summary", all four
processes reach that line, but only one of them has rank 0, so only one prints.

This style is called **SPMD** — Single Program, Multiple Data.

> The program does **not** create the processes. `mpirun` creates them all
> before the program starts. The program just asks "how many of us are there,
> and which one am I?"

---

## 3. The whole algorithm in one view

```
START (all processes are now running this same code)

    Ask MPI: what is my rank? how many processes are there?

    IF no number was given on the command line THEN
        IF I am rank 0 THEN print a usage message
        shut down MPI and exit
    END IF

    IF I am rank 0 THEN read n from the command line
    Broadcast n from rank 0 to every process

    Start the timer

    Work out which slices of numbers are mine
    FOR each of my slices:
        FOR each number in that slice:
            IF the number is prime THEN remember it
        END FOR
    END FOR

    Send all my primes to rank 0

    Stop the timer

    IF I am rank 0 THEN
        Sort the combined list
        Write it to primes_output.txt
        Print the summary line
    END IF

    Shut down MPI

END
```

---

## 4. Deciding if one number is prime

```
FUNCTION is_prime(value):

    IF value is less than 2 THEN
        RETURN not prime            // 0, 1 and negatives don't count
    END IF

    IF value equals 2 THEN
        RETURN prime                // 2 is the only even prime
    END IF

    IF value divides evenly by 2 THEN
        RETURN not prime            // all other even numbers are composite
    END IF

    limit = square root of value

    FOR divisor = 3, 5, 7, 9, ... up to limit:
        IF value divides evenly by divisor THEN
            RETURN not prime        // found a factor, stop early
        END IF
    END FOR

    RETURN prime                    // nothing divided it
```

**Why stop at the square root?** If `value = a × b` and *both* `a` and `b`
were bigger than `√value`, then `a × b` would be bigger than `value` — a
contradiction. So at least one factor is always `≤ √value`. If nothing up to
there divides it, nothing will.

**Why step by 2?** Even numbers were already ruled out, so only odd divisors
can possibly work. This halves the work.

**Cost:** roughly `√value` steps. This matters a lot — see section 6.

---

## 5. Splitting the work: the naive way, and why it's bad

The obvious approach with 4 processes and n = 1,000,000:

```
rank 0 checks       0 .. 249,999
rank 1 checks 250,000 .. 499,999
rank 2 checks 500,000 .. 749,999
rank 3 checks 750,000 .. 999,999
```

Each process gets the same *quantity* of numbers. But not the same *amount of
work*, because testing a big number costs more than testing a small one
(`√1,000,000` = 1000 steps, but `√10,000` = only 100 steps).

Measured, counting actual division steps:

| rank | work done | 
|---|---|
| 0 | 4,944,695 |
| 1 | 8,011,836 |
| 2 | 9,846,491 |
| 3 | 11,297,539 |

Rank 3 does **2.28× more work** than rank 0. And since rank 0 cannot produce
the final answer until everyone has reported in, three processes sit idle
waiting for rank 3. The program is only as fast as its slowest process.

---

## 6. Splitting the work: what this program actually does

Instead of 4 big blocks, cut the range into **many small slices** and deal
them out like playing cards.

```
number of slices = number of processes × 8
size of each slice = n ÷ number of slices, rounded up
```

With 4 processes that's 32 slices. They are dealt out like this:

```
slice:   0    1    2    3    4    5    6    7    8   ...
goes to: r0   r1   r2   r3   r0   r1   r2   r3   r0  ...
```

In pseudocode:

```
my_slices = every slice number starting at my rank,
            counting up by "number of processes" each time

// rank 0 gets slices 0, 4, 8, 12, 16, 20, 24, 28
// rank 1 gets slices 1, 5, 9, 13, 17, 21, 25, 29
// rank 2 gets slices 2, 6, 10, ...
// rank 3 gets slices 3, 7, 11, ...
```

Now every process gets a mixture of low numbers (cheap) and high numbers
(expensive), so they all finish at roughly the same moment.

The same measurement as before, with this scheme:

| rank | work done |
|---|---|
| 0 | 8,012,598 |
| 1 | 8,411,874 |
| 2 | 8,703,415 |
| 3 | 8,972,674 |

Imbalance drops from **2.28× to 1.12×**.

### Why 8 slices each, and not some other number?

More slices means finer mixing and better balance, with diminishing returns:

| slices per process | imbalance |
|---|---|
| 1 (= the naive way) | 2.28× |
| 2 | 1.52× |
| 4 | 1.24× |
| **8** | **1.12×** |
| 16 | 1.06× |
| 64 | 1.01× |

8 captures most of the available gain. This is the one number worth tuning
if the lab asks you to experiment.

### Scanning one slice

```
FOR each slice number assigned to me:

    first = slice number × slice size
    last  = first + slice size

    IF last is beyond n THEN
        last = n                    // the rounding-up can overshoot
    END IF

    IF first is below 2 THEN
        first = 2                   // skip 0 and 1, they aren't prime
    END IF

    FOR number = first up to (but not including) last:
        IF is_prime(number) THEN
            add number to my personal list
        END IF
    END FOR

END FOR
```

Two guards worth noting:
- **`last` clamp** — because slice size was rounded up, the final slices can
  run past `n`. Anything past `n` is trimmed off.
- **`first` clamp** — only ever affects slice 0, which would otherwise start
  at 0.

---

## 7. Storing the results: a list that grows

A process cannot know in advance how many primes it will find, so it uses a
list that expands on demand.

```
FUNCTION add_to_list(list, value):
    IF the list is completely full THEN
        double its capacity
    END IF
    put value at the end
    increase the count by 1
```

**Why double, rather than grow by one each time?** Growing by one means
copying the whole list on every single addition — very slow. Doubling means
resizing happens rarely (after 1024 items, then 2048, then 4096...), so the
average cost of adding one item stays tiny.

---

## 8. Collecting everything onto rank 0

This is the fiddly part, because **each process found a different number of
primes**. Rank 0 has to be told the sizes before it can receive the data.

So it happens in two rounds.

### Round 1 — gather the counts

```
Every process sends ONE number: "I found this many primes"
Rank 0 receives them into a list called counts

counts[0] = how many rank 0 found
counts[1] = how many rank 1 found
...
```

### Round 2 — work out the layout, then gather the primes

Rank 0 now calculates where each process's block will sit in the big combined
array. These positions are called **displacements**.

```
displs[0] = 0
FOR i = 1 up to number of processes - 1:
    displs[i] = displs[i-1] + counts[i-1]    // start where the last one ended
END FOR

total = displs[last] + counts[last]
make room for "total" primes
```

```
Every process sends its whole list of primes
Rank 0 receives them, placing process i's block at position displs[i]
```

### Worked example: n = 100, 4 processes

Each process ends up with:

```
rank 0:  2  3 17 19 67 83 97          (7 primes)
rank 1:  5  7 23 37 53 71             (6 primes)
rank 2: 11 41 43 59 73 89             (6 primes)
rank 3: 13 29 31 47 61 79             (6 primes)
```

So:

```
counts  = [ 7,  6,  6,  6 ]
displs  = [ 0,  7, 13, 19 ]
total   = 19 + 6 = 25 primes
```

And the combined array arrives looking like this:

```
2 3 17 19 67 83 97 | 5 7 23 37 53 71 | 11 41 43 59 73 89 | 13 29 31 47 61 79
└──── rank 0 ─────┘ └─── rank 1 ────┘ └──── rank 2 ─────┘ └──── rank 3 ────┘
```

---

## 9. Why a sort is needed at the end

Look at that combined array again. It starts `2, 3, 17, 19, 67, 83, 97, 5, ...`
— clearly **not** in ascending order.

Two things scrambled it:
1. Each process searched *scattered* slices, so its own list jumps around
   (rank 0 has 2, 3 then leaps to 17, 19).
2. The blocks are joined in rank order, so rank 1's small primes land *after*
   rank 0's large ones.

```
Sort the combined list into ascending order
```

The sorting routine needs to be told how to compare two values, because it
works on any type of data and has no idea what it is holding.

```
FUNCTION compare(a, b):
    IF a < b THEN RETURN "a comes first"
    IF a > b THEN RETURN "b comes first"
    RETURN "they are equal"
```

> A common bug is writing this as `RETURN a - b`. For large values that
> subtraction can overflow or get truncated, silently producing the wrong
> order. Comparing directly always works.

---

## 10. Writing the output

```
IF I am rank 0 THEN
    open primes_output.txt for writing
    IF the file would not open THEN
        print an error and give up on the file
    ELSE
        FOR each prime in the sorted list:
            write it on its own line
        END FOR
        close the file
    END IF
END IF
```

---

## 11. Timing

```
time_start = current time      // just after n has been shared out
    ... search for primes ...
    ... gather results onto rank 0 ...
    ... rank 0 sorts the list and writes the file ...
time_end   = current time      // after everything is finished
```

The timer covers the entire program, so the reported figure is the real cost of
producing the output rather than only the parallel portion.

Measured at n = 10,000,000 with 4 processes (median of several runs):

| stage | time | runs in parallel? |
|---|---|---|
| prime search (slowest rank) | 115 ms | yes |
| gather | 13 ms | partly |
| sort | 10 ms | **no** — rank 0 only |
| write file | 29 ms | **no** — rank 0 only |
| **total reported** | **162 ms** | |

The stages do not add up exactly to the total, because the search and the
gather overlap: ranks that finish searching early wait inside the gather while
slower ranks are still working.

About 39 ms of that 162 ms — roughly a quarter — is the sort and the file write,
which run on rank 0 alone and do not get any faster when processes are added.
That fixed cost is what limits the achievable speedup, and it is measured
directly in section 14.

---

## 12. The MPI operations used, in plain English

| Operation | What it does |
|---|---|
| **Init** | Start MPI. Must happen before any other MPI call. |
| **Comm_rank** | "Which process am I?" → 0, 1, 2, ... |
| **Comm_size** | "How many of us are there?" |
| **Bcast** | One process sends a value; everybody else receives a copy. |
| **Gather** | Everybody sends the *same amount*; one process collects it all. |
| **Gatherv** | Same, but each process may send a *different amount*. |
| **Wtime** | Read the wall clock, for timing. |
| **Finalize** | Shut MPI down cleanly. No MPI calls after this. |

All of these except `Wtime` are **collective**: every process must call them,
or the program will hang waiting for the missing one. This is why the
"no argument given" error path still calls `Finalize` on every process before
exiting, rather than just quitting on rank 0.

---

## 13. Summary of the design decisions

| Decision | Reason |
|---|---|
| Trial division up to `√value` | Correct and simple; anything above `√value` cannot be the smaller factor |
| Skip even numbers | Halves the divisor loop |
| Many small slices, dealt round-robin | Balances cheap small numbers against expensive large ones — 2.28× imbalance becomes 1.12× |
| 8 slices per process | Captures most of the balancing gain before returns diminish |
| Doubling list capacity | Number of primes is unknown ahead of time; doubling keeps appends cheap |
| Two-stage gather | Processes find different amounts, so sizes must be known before the data can be collected |
| Sort at the very end | Scattered slices plus rank-ordered blocks mean the gathered data is unordered |
| Only rank 0 writes the file | Prevents 4 processes from writing over each other |

---

## 14. Measured performance

Measured on an Apple M5 (4 performance cores, 6 efficiency cores) using Open
MPI 5.0.9, at n = 10,000,000. Each figure is the median of five runs, and
covers the whole program including the sort and the file write.

| processes | time (s) | speedup | efficiency |
|---|---|---|---|
| 1 | 0.4424 | 1.00x | 100.0% |
| 2 | 0.2568 | 1.72x | 86.1% |
| 3 | 0.1952 | 2.27x | 75.6% |
| 4 | 0.1616 | 2.74x | 68.4% |
| 5 | 0.1678 | 2.64x | 52.7% |
| 6 | 0.1623 | 2.73x | 45.4% |
| 7 | 0.1697 | 2.61x | 37.2% |
| 8 | 0.1656 | 2.67x | 33.4% |
| 9 | 0.1722 | 2.57x | 28.5% |
| 10 | 0.1739 | 2.54x | 25.4% |

Speedup improves steadily up to four processes, peaks at 2.74x, and then stops.
Everything from five processes upward sits at roughly 2.6x.

Two separate effects produce this shape.

### Effect 1: the serial portion (Amdahl's law)

The sort and the file write take about 39 ms and run on rank 0 alone. Against a
single-process total of 442 ms, that is a serial fraction of roughly **9%**.

Amdahl's law says the best achievable speedup with p processors is:

```
speedup  =           1
           -------------------
            f  +  (1 - f) / p          where f is the serial fraction
```

With f = 0.09 that gives a ceiling of about **11x even with unlimited
processors**, and predicts 1.84x, 2.55x and 3.16x for two, three and four
processes. The measured values (1.72x, 2.27x, 2.74x) sit just below those
predictions, the shortfall being the residual 1.12x load imbalance in the
distribution itself.

### Effect 2: heterogeneous cores

The plateau from five processes onward coincides exactly with the number of
performance cores. The M5 has four fast cores and six efficiency cores running
at roughly one third the speed.

The distribution hands every process an equal share of the numbers, because it
assumes every processor is equally fast. On this machine that is false. A
process placed on an efficiency core receives the same amount of work as one on
a performance core, takes about three times as long, and every other process
waits at the gather until it finishes.

Adding a processor that runs at one third speed therefore does not add one
third of a processor's throughput — it adds a straggler that sets the pace.
Four fast cores plus six slow ones perform no better than four fast cores alone.

Per-rank measurement confirms this. With four processes the slowest rank takes
1.10x as long as the fastest, almost exactly the 1.12x imbalance predicted by
the distribution itself. With eight processes, where every rank is given an
identical 1,250,000 numbers, the spread widens to 1.46x. That extra gap is not
the algorithm; it is the hardware.

### What this means

Neither effect is a flaw in the decomposition. The scheme balances the work it
can predict — that large numbers cost more than small ones — and does so well.

What it cannot do is shrink the serial tail, or react to processors that turn
out to run at different speeds, because every assignment is fixed before the
program begins. The second of these is exactly the condition under which
dynamic self-scheduling (Addendum E) would be preferable: a process on an
efficiency core would simply request fewer chunks, and the faster processes
would absorb the remainder.

---

# Addendum — Alternative Distribution Strategies

Other ways the work could have been divided, and how they compare. All figures
are for n = 1,000,000 with 4 processes, measured by counting actual division
steps performed by each rank. "Imbalance" is the busiest rank's work divided by
the idlest rank's — 1.00× would be perfect.

| Scheme | Imbalance | Verdict |
|---|---|---|
| Contiguous block | 2.285× | Simple, poorly balanced |
| **Block-cyclic, 8 blocks/proc (chosen)** | **1.120×** | Best measured |
| Pure cyclic (block size 1) | 67.241× | Catastrophic — see below |
| Folded / reversed pairing | 1.170× | Nearly as good, much simpler |
| Cost-weighted contiguous blocks | 1.172× | Good balance, keeps locality |

---

## A. Contiguous block — the obvious baseline

```
each rank takes one unbroken range:  rank r gets [r × n/p, (r+1) × n/p)
```

Simplest possible scheme, and the gathered results come back already sorted,
so no final sort is needed. But testing a number costs about √value divisions,
so the rank holding the top of the range does over twice the work of the rank
holding the bottom. Everyone waits for the slowest.

---

## B. Pure cyclic — a trap worth documenting

```
rank r takes numbers r, r+p, r+2p, r+3p, ...      (block size of 1)
```

Intuitively this should balance *better* than block-cyclic — it interleaves at
the finest possible granularity. Measured, it is **60× worse than doing nothing
clever at all**.

The reason is arithmetic, not scheduling. Rank `r` receives exactly the numbers
congruent to `r` modulo `p`. If `r` and `p` share any common factor, then every
single number in that set shares that factor too — so every number rank `r`
tests is composite, rejected almost immediately, and that rank does no real work.

Only the ranks whose number is **coprime to p** ever see a prime. The count of
those is Euler's totient function φ(p):

| p | φ(p) | ranks doing real work | imbalance |
|---|---|---|---|
| 2 | 1 | 1 of 2 | 67.20× |
| 3 | 2 | 2 of 3 | 50.69× |
| 4 | 2 | 2 of 4 | 67.24× |
| 5 | 4 | 4 of 5 | 31.74× |
| 6 | 2 | 2 of 6 | 100.37× |
| 7 | 6 | 6 of 7 | 24.71× |
| 8 | 4 | 4 of 8 | 67.27× |

With 6 processes, four of them finish almost instantly and two do all the work.
Note rank 0 is *always* idle regardless of p, because it receives only the
multiples of p — every one of which is composite.

**Lesson:** when work is distributed by a stride, check whether the stride
interacts with the structure of the data. Here the stride aliases against
divisibility. Using blocks larger than 1 destroys the alias completely, which
is a second, unplanned reason the chosen scheme works.

---

## C. Folded / reversed pairing

```
cut the range into 2p blocks
rank r takes block r AND block (2p - 1 - r)
```

Each rank gets one cheap low block paired with one expensive high block, so the
costs cancel out.

```
with p = 4:  rank 0 gets blocks 0 and 7
             rank 1 gets blocks 1 and 6
             rank 2 gets blocks 2 and 5
             rank 3 gets blocks 3 and 4
```

Measured at **1.170×** — almost matching the chosen scheme while assigning only
two ranges per rank instead of eight. Worth mentioning as the cheapest big win
available: one line of index arithmetic removes most of the imbalance.

---

## D. Cost-weighted contiguous blocks

Rather than giving each rank an equal *count* of numbers, give each an equal
predicted *cost*. Since cost grows like √value, the total cost up to some point
b grows like b^1.5, so the fair boundaries are:

```
boundary for rank i  =  n × (i / p) ^ (2/3)
```

With 4 processes the splits land at roughly 40%, 63% and 83% of the range,
rather than 25%, 50% and 75%.

Measured at **1.172×**, and it keeps every rank on one contiguous range —
better memory locality, and the gathered output is already sorted, so the final
sort could be dropped.

The drawback is that it depends on a cost model. It works here because the cost
of trial division is known in advance; it would not transfer to a problem whose
per-item cost cannot be predicted.

---

## E. Dynamic self-scheduling (master–worker)

```
rank 0 acts as a manager and hands out work on request:
    WHILE chunks remain:
        wait for any worker to report "done, send me more"
        send that worker the next chunk

every other rank:
    LOOP:
        ask the manager for a chunk
        IF none left THEN stop
        process it and report back
```

Balance is near-perfect by construction — a rank that finishes early simply
asks for more — and it adapts to conditions a static scheme cannot see: a
throttled core, a machine shared with another job, uneven hardware.

The costs are real though. Every chunk requires a request and a reply, so
communication grows with the number of chunks; the manager can become a
bottleneck at scale; and if rank 0 does nothing but hand out work, one
processor is lost to coordination.

*No imbalance figure is given here because it cannot be simulated statically —
the outcome depends on runtime timing and message latency.*

---

## F. Work stealing

The decentralised version of E. Every rank starts with a static share; a rank
that empties its queue steals from a randomly chosen busy rank. No central
manager, so no bottleneck, but it needs one-sided communication or a background
thread to service steal requests — significantly harder to implement in MPI
than the schemes above.

---

## G. A different algorithm entirely: segmented Sieve of Eratosthenes

Everything above assumes trial division. A sieve changes the question.

```
rank 0 sieves up to √n to obtain the "seed" primes
broadcast the seed primes to all ranks
each rank takes one contiguous segment of the range
    mark every multiple of every seed prime within that segment
    whatever stays unmarked is prime
```

Two consequences:

1. **It is far faster.** Sieving costs about n log log n operations overall,
   against roughly n^1.5 for trial division across the whole range.
2. **The balancing problem largely disappears.** The cost of sieving a segment
   depends on the segment's length, not on how large its numbers are, so plain
   contiguous blocks are already well balanced — no interleaving needed.

The catch is memory: each rank needs a mark array for its segment, which is why
the segmented form exists rather than one array of size n.

Worth noting in a report as the answer to "how would you make this genuinely
fast", as distinct from "how would you balance this better".

---

## Summary

The chosen scheme (static block-cyclic, 8 blocks per rank) is a sound choice:
it measured best, requires no communication during the search, and is only a
few lines of index arithmetic. Options C and D come within 5% of it with
different trade-offs. Option E wins whenever the machine itself is
unpredictable. Option G wins outright on raw speed, but answers a different
question.
