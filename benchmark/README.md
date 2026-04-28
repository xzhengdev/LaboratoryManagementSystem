# Benchmark 使用说明

## 1. 预约并发压测脚本

脚本路径：`benchmark/reservation_concurrency_benchmark.py`

作用：

1. 并发请求 `POST /api/reservations`。
2. 输出吞吐、P50/P95/P99 延迟、状态码分布。
3. 统计返回预约 ID 是否重复，验证幂等与冲突控制效果。

## 2. 运行示例

```bash
cd backend
python ..\benchmark\reservation_concurrency_benchmark.py ^
  --base-url http://127.0.0.1:5000 ^
  --username student1 ^
  --password 123456 ^
  --concurrency 100 ^
  --total 500 ^
  --campus-id 1 ^
  --lab-id 1 ^
  --date 2026-05-01 ^
  --start-time 09:00 ^
  --end-time 10:00 ^
  --idempotency-mode unique
```

说明：

1. `--idempotency-mode unique`：每次请求不同幂等键，观察高并发冲突控制。
2. `--idempotency-mode same`：所有请求同一幂等键，观察幂等去重能力。
3. `--idempotency-mode none`：不传幂等键，观察纯并发冲突控制行为。

