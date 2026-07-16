# EDTA Four-Tier Benchmark Report

## Run `2026-07-09T03:30:24Z`

- Environment: `render`
- Base URL: `https://edta-api.onrender.com`
- Workers: `2`
- Requests per worker: `3`
- Overall pass: `False`

| Tier | Requests | p50 (ms) | p95 (ms) | p95 budget | Throughput (rps) | Error rate | Fallback rate | Tier match | Avg confidence | Alignment top-1 | Rules fired avg | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| rules | 6 | 997.76 | 1001.13 | 250.00 | 0.96 | 0.00 | 0.00 | 1.00 | 0.96 | 1.00 | 2.00 | no |
| ml | 6 | 1321.79 | 1356.24 | 1500.00 | 0.70 | 0.00 | 0.00 | 1.00 | 0.52 | 1.00 | 0.00 | yes |
| slm | 6 | 1410.26 | 1416.47 | 800.00 | 0.69 | 0.00 | 1.00 | 1.00 | 0.94 | 1.00 | 1.00 | no |
| llm | 6 | 7263.19 | 7706.18 | 8000.00 | 0.15 | 0.00 | 0.00 | 0.00 | 0.65 | n/a | 0.00 | yes |
