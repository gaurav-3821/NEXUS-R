# Concurrency Scaling Report — Phase B

## Results

| Tasks | Time (s) | Throughput (/s) | Success (%) | p50 (ms) | p95 (ms) | Mem +MB | Chains |
|-------|----------|-----------------|-------------|----------|----------|---------|--------|
| 20 | 25.6 | 0.8 | 90.0 | 25646.8 | 25646.8 | 3.6 | OK |
| 50 | 68.5 | 0.7 | 90.0 | 68465.5 | 68465.5 | 6.5 | OK |
| 100 | 129.7 | 0.8 | 90.0 | 129647.5 | 129647.5 | 4.0 | OK |
| 200 | 332.3 | 0.6 | 90.0 | 332276.1 | 332276.1 | 9.0 | OK |

## Abort Conditions
Aborted: NO

## Degradation
Throughput cliff: NO
Memory baseline: 53.9MB

## Latency Percentiles
  20 tasks: p50=25646.8ms, p95=25646.8ms, p99=0.0ms
  50 tasks: p50=68465.5ms, p95=68465.5ms, p99=0.0ms
  100 tasks: p50=129647.5ms, p95=129647.5ms, p99=129647.5ms
  200 tasks: p50=332276.1ms, p95=332276.1ms, p99=332276.1ms