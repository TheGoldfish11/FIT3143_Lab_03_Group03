# Colab T4 benchmark results

**Setup:** Google Colab, NVIDIA Tesla T4 (40 SMs, PCIe 3.0), program `../1a/transfer_bench.cu`.
Synthetic RGB image buffers at 1080p (6.2 MB), 4K (24.9 MB) and 8K (99.5 MB); timing depends on size, not pixel content.
Each copy and kernel timing is the average of 10 runs; the batch tests process 12 images.

**What it measured:**
1. Copying an image to and from the GPU from normal (pageable) vs pinned memory
2. Bandwidth inside GPU memory, compared with the PCIe link
3. The rotation kernel (30°, one thread per pixel) on its own
4. A batch of 12 images: one at a time vs overlapped across 3 CUDA streams

| File | Shows |
|---|---|
| `1_pageable_vs_pinned.csv` | Pinned memory uploads ~2.5× faster |
| `2_bandwidth_8k.csv` | PCIe (~12 GB/s) vs GPU memory (~237 GB/s) |
| `3_copies_vs_kernel.csv` | 88–92% of the time is spent copying |
| `4_streams.csv` | Streams give ~1.75–1.8× throughput |
| `raw_results.csv` | All measurements |
