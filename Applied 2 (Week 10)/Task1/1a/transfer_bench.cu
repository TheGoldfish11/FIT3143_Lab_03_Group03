// FIT3143 Applied 2 - Task 1a
// Host <-> device transfer benchmark for one high-resolution RGB image.
//
// Measures:
//   1. Pageable vs pinned host memory: H2D and D2H bandwidth over PCIe
//   2. Device-to-device copy bandwidth (GPU memory, for comparison with PCIe)
//   3. A batch of images: synchronous (one stream) vs pinned + cudaMemcpyAsync
//      on several streams, so copies overlap with the rotation kernel
//
// Build: nvcc -O2 -o transfer_bench transfer_bench.cu
// Run:   ./transfer_bench [width] [height] [images] [streams]
//        defaults: 7680 4320 12 3   (8K UHD RGB, ~100 MB per image)

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <cuda_runtime.h>

#define CHECK(call)                                                          \
    do {                                                                     \
        cudaError_t err_ = (call);                                           \
        if (err_ != cudaSuccess) {                                           \
            fprintf(stderr, "CUDA error \"%s\" at %s:%d\n",                  \
                    cudaGetErrorString(err_), __FILE__, __LINE__);           \
            exit(EXIT_FAILURE);                                              \
        }                                                                    \
    } while (0)

static const int REPS = 10;

// Rotate about the image centre using inverse mapping (nearest neighbour).
// The output keeps the input size, so the rotated corners are cropped; that
// is enough here because Task 1a is about moving the data, not the kernel.
__global__ void rotate(const uchar3* src, uchar3* dst, int w, int h, float c, float s)
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= w || y >= h) return;

    float dx = x - 0.5f * w;
    float dy = y - 0.5f * h;
    int sx = __float2int_rn( c * dx + s * dy + 0.5f * w);   // R(-theta)
    int sy = __float2int_rn(-s * dx + c * dy + 0.5f * h);

    dst[y * w + x] = (sx >= 0 && sx < w && sy >= 0 && sy < h)
                     ? src[sy * w + sx] : make_uchar3(0, 0, 0);
}

// Average time (ms) of REPS synchronous copies, measured with CUDA events.
static float time_copy(void* dst, const void* src, size_t bytes, cudaMemcpyKind kind)
{
    cudaEvent_t start, stop;
    CHECK(cudaEventCreate(&start));
    CHECK(cudaEventCreate(&stop));

    CHECK(cudaMemcpy(dst, src, bytes, kind));               // warm-up
    CHECK(cudaEventRecord(start));
    for (int r = 0; r < REPS; r++)
        CHECK(cudaMemcpy(dst, src, bytes, kind));
    CHECK(cudaEventRecord(stop));
    CHECK(cudaEventSynchronize(stop));

    float ms = 0.0f;
    CHECK(cudaEventElapsedTime(&ms, start, stop));
    CHECK(cudaEventDestroy(start));
    CHECK(cudaEventDestroy(stop));
    return ms / REPS;
}

static double gbps(size_t bytes, float ms) { return (double)bytes / 1e9 / (ms / 1e3); }

int main(int argc, char** argv)
{
    int w        = argc > 1 ? atoi(argv[1]) : 7680;
    int h        = argc > 2 ? atoi(argv[2]) : 4320;
    int nImages  = argc > 3 ? atoi(argv[3]) : 12;
    int nStreams = argc > 4 ? atoi(argv[4]) : 3;
    size_t bytes = (size_t)w * h * sizeof(uchar3);

    cudaDeviceProp prop;
    CHECK(cudaGetDeviceProperties(&prop, 0));
    printf("GPU: %s | copy engines (asyncEngineCount): %d | SMs: %d\n",
           prop.name, prop.asyncEngineCount, prop.multiProcessorCount);
    printf("Image: %d x %d RGB = %.1f MB\n\n", w, h, bytes / 1e6);

    // ---------------- 1. pageable vs pinned ----------------
    unsigned char* hPageable = (unsigned char*)malloc(bytes);      // ordinary memory
    unsigned char* hPinned;
    CHECK(cudaMallocHost(&hPinned, bytes));                        // page-locked memory
    if (!hPageable) { fprintf(stderr, "malloc failed\n"); return EXIT_FAILURE; }
    for (size_t i = 0; i < bytes; i++) hPageable[i] = hPinned[i] = (unsigned char)(i * 31);

    uchar3 *dA, *dB;
    CHECK(cudaMalloc(&dA, bytes));
    CHECK(cudaMalloc(&dB, bytes));

    float tPageH2D = time_copy(dA, hPageable, bytes, cudaMemcpyHostToDevice);
    float tPageD2H = time_copy(hPageable, dA, bytes, cudaMemcpyDeviceToHost);
    float tPinH2D  = time_copy(dA, hPinned,   bytes, cudaMemcpyHostToDevice);
    float tPinD2H  = time_copy(hPinned,   dA, bytes, cudaMemcpyDeviceToHost);
    float tD2D     = time_copy(dB, dA,        bytes, cudaMemcpyDeviceToDevice);

    printf("%-28s %10s %10s\n", "Transfer", "ms/image", "GB/s");
    printf("%-28s %10.2f %10.1f\n", "H2D pageable (malloc)",      tPageH2D, gbps(bytes, tPageH2D));
    printf("%-28s %10.2f %10.1f\n", "D2H pageable (malloc)",      tPageD2H, gbps(bytes, tPageD2H));
    printf("%-28s %10.2f %10.1f\n", "H2D pinned (cudaMallocHost)", tPinH2D,  gbps(bytes, tPinH2D));
    printf("%-28s %10.2f %10.1f\n", "D2H pinned (cudaMallocHost)", tPinD2H,  gbps(bytes, tPinD2H));
    // A device-to-device copy reads and writes every byte, so count it twice.
    printf("%-28s %10.2f %10.1f  (read + write)\n", "D2D in GPU memory", tD2D, gbps(2 * bytes, tD2D));

    // ---------------- 2. batch: synchronous vs streams ----------------
    float theta = 30.0f * (float)M_PI / 180.0f;
    float c = cosf(theta), s = sinf(theta);
    dim3 block(16, 16);
    dim3 grid((w + block.x - 1) / block.x, (h + block.y - 1) / block.y);

    // Each stream owns its own pinned input/output buffers and device buffers,
    // so image i (on stream i % nStreams) never overwrites another stream's data.
    cudaStream_t* streams = (cudaStream_t*)malloc(nStreams * sizeof(cudaStream_t));
    unsigned char **hIn = (unsigned char**)malloc(nStreams * sizeof(unsigned char*));
    unsigned char **hOut = (unsigned char**)malloc(nStreams * sizeof(unsigned char*));
    uchar3 **dIn = (uchar3**)malloc(nStreams * sizeof(uchar3*));
    uchar3 **dOut = (uchar3**)malloc(nStreams * sizeof(uchar3*));
    for (int k = 0; k < nStreams; k++) {
        CHECK(cudaStreamCreate(&streams[k]));
        CHECK(cudaMallocHost(&hIn[k], bytes));
        CHECK(cudaMallocHost(&hOut[k], bytes));
        CHECK(cudaMalloc(&dIn[k], bytes));
        CHECK(cudaMalloc(&dOut[k], bytes));
        memcpy(hIn[k], hPinned, bytes);
    }

    cudaEvent_t start, stop;
    CHECK(cudaEventCreate(&start));
    CHECK(cudaEventCreate(&stop));

    // Kernel time alone (no transfers)
    rotate<<<grid, block>>>(dIn[0], dOut[0], w, h, c, s);          // warm-up
    CHECK(cudaGetLastError());
    CHECK(cudaEventRecord(start));
    for (int r = 0; r < REPS; r++)
        rotate<<<grid, block>>>(dIn[0], dOut[0], w, h, c, s);
    CHECK(cudaEventRecord(stop));
    CHECK(cudaEventSynchronize(stop));
    float tKernel;
    CHECK(cudaEventElapsedTime(&tKernel, start, stop));
    tKernel /= REPS;

    // (A) synchronous: copy in, rotate, copy out, one image at a time
    CHECK(cudaEventRecord(start));
    for (int i = 0; i < nImages; i++) {
        CHECK(cudaMemcpy(dIn[0], hIn[0], bytes, cudaMemcpyHostToDevice));
        rotate<<<grid, block>>>(dIn[0], dOut[0], w, h, c, s);
        CHECK(cudaMemcpy(hOut[0], dOut[0], bytes, cudaMemcpyDeviceToHost));
    }
    CHECK(cudaEventRecord(stop));
    CHECK(cudaEventSynchronize(stop));
    float tSync;
    CHECK(cudaEventElapsedTime(&tSync, start, stop));

    // (B) asynchronous: the same work spread over nStreams streams
    CHECK(cudaEventRecord(start));
    for (int i = 0; i < nImages; i++) {
        int k = i % nStreams;
        CHECK(cudaMemcpyAsync(dIn[k], hIn[k], bytes, cudaMemcpyHostToDevice, streams[k]));
        rotate<<<grid, block, 0, streams[k]>>>(dIn[k], dOut[k], w, h, c, s);
        CHECK(cudaMemcpyAsync(hOut[k], dOut[k], bytes, cudaMemcpyDeviceToHost, streams[k]));
    }
    CHECK(cudaDeviceSynchronize());
    CHECK(cudaEventRecord(stop));
    CHECK(cudaEventSynchronize(stop));
    float tAsync;
    CHECK(cudaEventElapsedTime(&tAsync, start, stop));
    CHECK(cudaGetLastError());

    printf("\nRotation kernel alone: %.3f ms/image (%.1f GB/s effective, read + write)\n",
           tKernel, gbps(2 * bytes, tKernel));
    printf("Batch of %d images (pinned, H2D + rotate + D2H):\n", nImages);
    printf("  synchronous, 1 stream : %8.2f ms total, %6.2f ms/image\n", tSync, tSync / nImages);
    printf("  async, %d streams      : %8.2f ms total, %6.2f ms/image  (%.2fx faster)\n",
           nStreams, tAsync, tAsync / nImages, tSync / tAsync);
    printf("  share of synchronous time spent on PCIe copies: %.0f%%\n",
           100.0 * (1.0 - tKernel * nImages / tSync));

    // CSV line for graphs: w,h,MB,pageH2D,pageD2H,pinH2D,pinD2H,d2d,kernel,sync,async (ms)
    printf("\nCSV,%d,%d,%.1f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f\n",
           w, h, bytes / 1e6, tPageH2D, tPageD2H, tPinH2D, tPinD2H, tD2D, tKernel,
           tSync / nImages, tAsync / nImages);

    for (int k = 0; k < nStreams; k++) {
        CHECK(cudaStreamDestroy(streams[k]));
        CHECK(cudaFreeHost(hIn[k]));
        CHECK(cudaFreeHost(hOut[k]));
        CHECK(cudaFree(dIn[k]));
        CHECK(cudaFree(dOut[k]));
    }
    free(streams); free(hIn); free(hOut); free(dIn); free(dOut);
    CHECK(cudaEventDestroy(start));
    CHECK(cudaEventDestroy(stop));
    CHECK(cudaFree(dA));
    CHECK(cudaFree(dB));
    CHECK(cudaFreeHost(hPinned));
    free(hPageable);
    return 0;
}
