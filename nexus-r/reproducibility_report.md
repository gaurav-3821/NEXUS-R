# Benchmark Reproducibility Report

**Date:** 2026-05-24 07:54 UTC  

**Passes:** 10  |  **Prompts per pass:** 4  |  **Overall stable:** PASS


## Standard Pass Results

| Pass | Success | Avg Latency (ms) | Routing |
|------|---------|-------------------|---------|
| 0 | 4/4 | 3317 | ollama/qwen2.5:1.5b-instruct |
| 1 | 4/4 | 3571 | ollama/qwen2.5:1.5b-instruct |
| 2 | 4/4 | 3667 | ollama/qwen2.5:1.5b-instruct |
| 3 | 4/4 | 3620 | ollama/qwen2.5:1.5b-instruct |
| 4 | 4/4 | 3714 | ollama/qwen2.5:1.5b-instruct |
| 5 | 4/4 | 3538 | ollama/qwen2.5:1.5b-instruct |
| 6 | 4/4 | 3594 | ollama/qwen2.5:1.5b-instruct |
| 7 | 4/4 | 3672 | ollama/qwen2.5:1.5b-instruct |
| 8 | 4/4 | 3385 | ollama/qwen2.5:1.5b-instruct |
| 9 | 4/4 | 3373 | ollama/qwen2.5:1.5b-instruct |

## Variance Metrics

| Prompt | Mean (ms) | Std (ms) | CV | Stable | Successful Runs |
|--------|-----------|----------|----|--------|-----------------|
| hello world | 3796.4 | 326.1 | 0.0859 | PASS | 10/10 |
| explain what a database is in one senten | 3867.1 | 174.2 | 0.045 | PASS | 10/10 |
| draft a short commit message | 3905.7 | 160.8 | 0.0412 | PASS | 10/10 |
| list all python files | 2611.3 | 128.2 | 0.0491 | PASS | 10/10 |

## Cost Reproducibility

- Mean cost: $0.080000
- Std dev: $0.000000
- CV: 0.0000

## Load Impact

- Under concurrent load: 4/4 success

## Restart Persistence

- Session ID persists: True
- History count before restart: 1
- History count after restart: 1

## Verdict

**Reproducibility confidence:** HIGH  

**Same hardware, same OS, same load:** Verified  

**CV threshold (10%):** MET  
