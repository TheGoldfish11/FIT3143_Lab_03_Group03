# Task 1a: Moving image data between host memory (DDR5) and GPU memory (GDDR)

## 1. Key idea

The CPU and the GPU have **physically separate memories** (a *discrete* GPU). Before a kernel can rotate an
image, the pixels must be copied from host DRAM (DDR5) into device DRAM (GDDR6/GDDR5) over the **PCIe
bus**, and the rotated result must be copied back. These copies are done by the GPU's **copy (DMA)
engines** and are the slowest link in the chain. For a light, **memory-bound** kernel like rotation, they
take more time than the computation.

*Diagram: `diagram_1a_transfer_path.png`*

## 2. Hardware involved

| Component | Role | Typical bandwidth |
|---|---|---|
| Host DRAM (DDR5 SDRAM) | Holds the decoded image (`h_img`) | ≈ 77 GB/s (dual-channel DDR5-4800 = 4800 MT/s × 8 B × 2) |
| PCIe root complex (on CPU die) | Connects the CPU and memory to the GPU | n/a |
| PCIe 4.0 x16 link | Bus between host and device; **full duplex** (both directions at once) | ≈ 31.5 GB/s each way (16 GT/s × 16 lanes × 128/130 ÷ 8); Gen5 ≈ 63 GB/s |
| GPU copy engines | DMA engines that move data over PCIe **without using the CPU or the SMs**. Most GPUs have 2, one per direction (`asyncEngineCount`) | n/a |
| Device DRAM (GDDR6/6X, VRAM) | Holds `d_src` / `d_dst` for the kernel | ≈ 0.5–1 TB/s (RTX 4090: 1008 GB/s); HBM3 on H100: ≈ 3.35 TB/s |

**PCIe is about 15–30× slower than the GPU's own memory.** The fewer bytes that cross it, the better.

## 3. The transfer, step by step

Numbers match the diagram.

**Pageable host memory** (`malloc`/`new`, the default case):

1. The OS can swap or move pageable pages at any time, so the GPU cannot DMA from them safely. The CUDA
   driver first **copies the image with the CPU into a hidden pinned "staging" buffer**. This is an extra
   copy that costs CPU time and DDR5 bandwidth.
2. **Host → Device (H2D):** a copy engine **DMAs** the staging buffer over PCIe into `d_src` in VRAM.
   `cudaMemcpy` blocks the host until the copy finishes.
3. **Kernel:** the SMs read `d_src` and write `d_dst` through the L2 cache at VRAM bandwidth.
4. **Device → Host (D2H):** a copy engine DMAs `d_dst` back over PCIe, through the staging buffer again.

```cuda
unsigned char* h_img = (unsigned char*)malloc(bytes);   // pageable
cudaMalloc(&d_src, bytes);  cudaMalloc(&d_dst, bytes);   // device memory (GDDR)
cudaMemcpy(d_src, h_img, bytes, cudaMemcpyHostToDevice); // steps 1 + 2
rotate<<<grid, block>>>(d_src, d_dst, w, h, c, s);       // step 3
cudaMemcpy(h_img, d_dst, bytes, cudaMemcpyDeviceToHost); // step 4
```

**Pinned (page-locked) host memory** (`cudaMallocHost` / `cudaHostRegister`) **removes step 1**. The pages
have fixed physical addresses, so the copy engine DMAs straight from the image buffer. This gives higher
bandwidth, and it is **required for asynchronous copies**.

```cuda
unsigned char* h_img;
cudaMallocHost(&h_img, bytes);                            // pinned: direct DMA, no staging copy
```

Trade-off: pinned memory cannot be paged out. Pinning too much starves the OS, so pin a few reusable
buffers rather than every image.

## 4. Overlapping transfers with computation (CUDA streams)

A company rotating huge numbers of images per day cares about **throughput**. With pinned buffers,
`cudaMemcpyAsync` and several **streams**, the copy engines and the SMs work at the same time. The upload
of image *i+1*, the rotation of image *i* and the download of image *i−1* overlap, a 3-stage **pipeline**.

```cuda
for (int i = 0; i < nImages; i++) {
    int k = i % nStreams;                                 // round-robin over streams
    cudaMemcpyAsync(d_in[k], h_in[k], bytes, cudaMemcpyHostToDevice, stream[k]);
    rotate<<<grid, block, 0, stream[k]>>>(d_in[k], d_out[k], w, h, c, s);
    cudaMemcpyAsync(h_out[k], d_out[k], bytes, cudaMemcpyDeviceToHost, stream[k]);
}
cudaDeviceSynchronize();
```

*Diagram: `diagram_1a_streams_timeline.png`*

The illustrative timeline uses 3 × 8K images: 25.2 ms sequentially vs 16.4 ms with streams. In steady
state that is one image every ~4 ms instead of ~8.4 ms. The link is still the bottleneck, because the SMs
are busy only ~10% of the time.

## 5. Worked example: one 8K image

- Size: 7680 × 4320 px × 3 B (RGB) = **99.5 MB**
- PCIe 4.0 at ~25 GB/s achieved: **~4 ms each way, ~8 ms round trip**
- Kernel: reads and writes ~100 MB each at ~0.5–1 TB/s: **~0.2–0.4 ms**

So **over 90% of the time is spent moving data, not rotating it**. This is Amdahl's law: the transfer is the
serial part that limits the speed-up (the link to 1b). It also motivates:
- keeping images resident on the GPU across a whole pipeline (decode → rotate → resize → encode)
- batching and overlapping transfers with streams
- sending compressed data (JPEG) and decoding on the GPU (nvJPEG)
- removing the CPU from the storage path entirely (GPUDirect Storage, 1c)

## 6. Other host ↔ device mechanisms (brief)

| Mechanism | API | How data moves | Fit for image rotation |
|---|---|---|---|
| Pageable copy | `malloc` + `cudaMemcpy` | CPU staging copy + DMA, blocking | Simple baseline, slowest |
| Pinned copy | `cudaMallocHost` + `cudaMemcpy` | Direct DMA | Faster single transfers |
| Pinned async + streams | `cudaMemcpyAsync` + `cudaStream_t` | DMA overlapped with kernels | **Best for batches of images** |
| Unified Memory | `cudaMallocManaged` | Pages migrate on demand when the GPU page-faults (Pascal+) | Easy to code; faults are slow unless prefetched with `cudaMemPrefetchAsync` |
| Zero-copy (mapped) | `cudaHostAlloc(..., cudaHostAllocMapped)` | Kernel reads host RAM directly over PCIe on every access | Poor: rotation's scattered (uncoalesced) reads become many small PCIe transactions |

## 7. Slide script (~40 s)

> "CPU and GPU memories are separate, joined by PCIe. With ordinary pageable memory the driver first copies
> the image into a pinned staging buffer, then a GPU copy engine DMAs it over PCIe into GDDR. The SMs rotate
> it at around 1 TB/s, and a copy engine DMAs the result back. PCIe gives only about 32 GB/s, so for an
> 8K image the two copies take about 8 ms while the kernel takes under half a millisecond. That is why we
> use pinned memory to remove the staging copy, and streams to overlap transfers with computation."

## 8. Likely Q&A for 1a

- **Why can't the GPU DMA from pageable memory?** The OS may move or swap the page mid-transfer. DMA needs
  fixed physical addresses, so the driver copies the data into pinned memory first.
- **Why not pin everything?** Pinned pages cannot be swapped out, so over-pinning reduces memory available
  to the OS and other processes and can hurt system performance.
- **What is a copy engine?** A DMA engine on the GPU that moves data over PCIe independently of the SMs and
  CPU. Two engines allow H2D and D2H at the same time (PCIe is full duplex).
- **Is `cudaMemcpy` synchronous?** Yes, it blocks the host. `cudaMemcpyAsync` returns immediately but only
  truly overlaps with pinned memory and a non-default stream.
- **Which is the bottleneck for rotation, PCIe or the kernel?** PCIe. It is ~15–30× slower than VRAM, and
  rotation does very little arithmetic per byte.
- **Unified Memory vs explicit copies?** Same PCIe link underneath. Unified Memory just migrates pages on
  demand, which is convenient but can be slower without prefetching.

## 9. Measuring it (optional, strengthens 1a and 1b)

`transfer_bench.cu` measures pageable vs pinned H2D/D2H, device-to-device bandwidth, kernel-only time and
a batch run with and without streams. On a CAAS GPU node:

```bash
sbatch run_transfer_bench.sh            # check the module/partition names in the script first
```

Use the measured numbers on the slide in place of the illustrative ones above.

## References

[1] NVIDIA, "CUDA C++ Programming Guide: Page-Locked Host Memory; Asynchronous Concurrent Execution,"
    NVIDIA Docs. https://docs.nvidia.com/cuda/cuda-c-programming-guide/

[2] NVIDIA, "CUDA C++ Best Practices Guide: Data Transfer Between Host and Device," NVIDIA Docs.
    https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/

[3] M. Harris, "How to Optimize Data Transfers in CUDA C/C++," NVIDIA Technical Blog, Dec. 2012.
    https://developer.nvidia.com/blog/how-optimize-data-transfers-cuda-cc/

[4] M. Harris, "How to Overlap Data Transfers in CUDA C/C++," NVIDIA Technical Blog, Dec. 2012.
    https://developer.nvidia.com/blog/how-overlap-data-transfers-cuda-cc/

[5] M. Harris, "Unified Memory for CUDA Beginners," NVIDIA Technical Blog, Jun. 2017.
    https://developer.nvidia.com/blog/unified-memory-cuda-beginners/

[6] PCI-SIG, "PCI Express Base Specification, Revision 4.0," 2017 (16 GT/s per lane, 128b/130b encoding).

[7] NVIDIA, "NVIDIA Ada GPU Architecture" whitepaper, 2022 (GeForce RTX 4090: 1008 GB/s GDDR6X).
