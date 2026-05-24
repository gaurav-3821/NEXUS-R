# EventStore Scaling Report — Phase B

## Batch Append Latency

| Batch Size | Total (ms) | Per Event (us) |
|------------|------------|----------------|
| 1 | 16.718 | 16718.1 |
| 10 | 1.171 | 117.11 |
| 100 | 9.496 | 94.96 |
| 1000 | 164.255 | 164.26 |

## Bulk Ingest

| Target Events | Time (ms) | Per Event (us) |
|---------------|-----------|----------------|
| 5000 | 248.9 | 64.01 |
| 10000 | 276.8 | 55.37 |
| 20000 | 474.7 | 47.47 |
| 50000 | 1202.7 | 40.09 |
| 100000 | 2046.7 | 40.93 |

## Retrieval

- Query by type (perf_test): 48.4ms
- Query by type (bulk_test): 3021.7ms
- Query by time range: 1615.8ms
- Chain retrieval: 1.7ms

## Storage

- Total events: 100000
- Database: 90.69MB
- WAL: 29.86MB
- Bytes/event: 951