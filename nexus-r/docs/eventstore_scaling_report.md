# EventStore Scaling Report — Phase B

## Batch Append Latency

| Batch Size | Total (ms) | Per Event (us) |
|------------|------------|----------------|
| 1 | 0.768 | 768.3 |
| 10 | 0.775 | 77.55 |
| 100 | 2.545 | 25.45 |
| 1000 | 24.333 | 24.33 |

## Bulk Ingest

| Target Events | Time (ms) | Per Event (us) |
|---------------|-----------|----------------|
| 5000 | 82.2 | 21.15 |
| 10000 | 196.5 | 39.3 |
| 20000 | 279.7 | 27.97 |
| 50000 | 921.1 | 30.7 |

## Retrieval

- Query by type (perf_test): 16.1ms
- Query by type (bulk_test): 589.3ms
- Query by time range: 10.6ms
- Chain retrieval: 0.9ms

## Storage

- Total events: 50000
- Database: 22.66MB
- WAL: 14.50MB
- Bytes/event: 475