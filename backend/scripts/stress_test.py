"""
并发压力测试脚本
目标: 验证系统在100并发用户下的表现
用法: python scripts/stress_test.py --concurrency 100 --requests 1000
"""
import asyncio
import aiohttp
import time
import argparse
import statistics
from collections import defaultdict
from datetime import datetime


BASE_URL = "http://localhost:8000"
ENDPOINTS = [
    {"path": "/api/v1/chat", "method": "POST", "body": {"message": "Where is my order?", "language": "en"}},
    {"path": "/api/v1/chat", "method": "POST", "body": {"message": "¿Dónde está mi pedido?", "language": "es"}},
    {"path": "/api/v1/listing/generate", "method": "POST", "body": {"product_name": "Wireless Earbuds Pro", "category": "Electronics", "key_features": ["Noise Cancelling", "30h Battery", "IPX5"]}},
    {"path": "/api/v1/products/recommendations?limit=5", "method": "GET"},
    {"path": "/api/v1/reports/dashboard?hours=168", "method": "GET"},
]


async def single_request(session: aiohttp.ClientSession, endpoint: dict) -> dict:
    start = time.monotonic()
    try:
        path = endpoint["path"]
        method = endpoint["method"]
        body = endpoint.get("body")

        if method == "GET":
            async with session.get(f"{BASE_URL}{path}") as resp:
                elapsed = time.monotonic() - start
                return {
                    "success": resp.status == 200,
                    "status": resp.status,
                    "latency_ms": elapsed * 1000,
                    "endpoint": path
                }
        else:
            async with session.post(f"{BASE_URL}{path}", json=body) as resp:
                elapsed = time.monotonic() - start
                return {
                    "success": resp.status == 200,
                    "status": resp.status,
                    "latency_ms": elapsed * 1000,
                    "endpoint": path
                }
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start
        return {
            "success": False,
            "status": 0,
            "latency_ms": elapsed * 1000,
            "endpoint": endpoint["path"],
            "error": "timeout"
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "success": False,
            "status": 0,
            "latency_ms": elapsed * 1000,
            "endpoint": endpoint["path"],
            "error": str(e)[:100]
        }


async def worker(worker_id: int, queue: asyncio.Queue, session: aiohttp.ClientSession, results: list):
    while True:
        endpoint = await queue.get()
        result = await single_request(session, endpoint)
        result["worker_id"] = worker_id
        results.append(result)
        queue.task_done()


async def run_stress_test(concurrency: int, total_requests: int):
    print(f"\n{'='*70}")
    print(f"  压力测试: {concurrency} 并发, {total_requests} 总请求")
    print(f"  目标: P99 < 3000ms, 错误率 < 1%")
    print(f"{'='*70}\n")

    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit=concurrency, limit_per_host=concurrency)

    queue = asyncio.Queue()
    results = []

    for i in range(total_requests):
        ep = ENDPOINTS[i % len(ENDPOINTS)]
        queue.put_nowait(ep.copy())

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        workers = [asyncio.create_task(worker(i, queue, session, results)) for i in range(concurrency)]

        start = time.monotonic()
        await queue.join()
        elapsed = time.monotonic() - start

        for w in workers:
            w.cancel()

    return analyze_results(results, elapsed, concurrency, total_requests)


def analyze_results(results: list, elapsed: float, concurrency: int, total_requests: int):
    if not results:
        print("没有结果返回！")
        return

    latencies = [r["latency_ms"] for r in results]
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    success_rate = len(successes) / len(results) * 100
    rps = len(results) / elapsed

    print(f"{'-'*70}")
    print(f"  总体结果")
    print(f"{'-'*70}")
    print(f"  总请求:        {len(results)}")
    print(f"  成功:          {len(successes)}  ({success_rate:.1f}%)")
    print(f"  失败:          {len(failures)}  ({100-success_rate:.1f}%)")
    print(f"  总耗时:        {elapsed:.2f}s")
    print(f"  吞吐量:        {rps:.1f} req/s")
    print(f"  并发数:        {concurrency}")
    print()
    print(f"  延迟统计 (ms):")
    print(f"    平均值:      {statistics.mean(latencies):.1f}")
    print(f"    中位数:      {statistics.median(latencies):.1f}")
    print(f"    P90:         {sorted(latencies)[int(len(latencies)*0.9)]:.1f}")
    print(f"    P95:         {sorted(latencies)[int(len(latencies)*0.95)]:.1f}")
    print(f"    P99:         {sorted(latencies)[int(len(latencies)*0.99)]:.1f}")
    print(f"    最大值:      {max(latencies):.1f}")
    print(f"    最小值:      {min(latencies):.1f}")

    by_endpoint = defaultdict(list)
    for r in results:
        by_endpoint[r["endpoint"]].append(r)

    print(f"\n  按端点详情:")
    print(f"  {'Endpoint':<45} {'Count':>6} {'Avg(ms)':>9} {'P99(ms)':>9} {'Err%':>7}")
    print(f"  {'-'*77}")
    for ep, ep_results in sorted(by_endpoint.items()):
        ep_lat = [r["latency_ms"] for r in ep_results]
        ep_ok = [r for r in ep_results if r["success"]]
        ep_err_rate = (len(ep_results) - len(ep_ok)) / len(ep_results) * 100
        ep_p99 = sorted(ep_lat)[int(len(ep_lat)*0.99)]
        print(f"  {ep:<45} {len(ep_results):>6} {statistics.mean(ep_lat):>9.1f} {ep_p99:>9.1f} {ep_err_rate:>6.1f}%")

    if failures:
        print(f"\n  失败请求样例 (前5):")
        for f in failures[:5]:
            print(f"    [{f.get('error', f['status'])}] {f['endpoint']}  ({f['latency_ms']:.0f}ms)")

    p99_ok = sorted(latencies)[int(len(latencies)*0.99)] < 3000
    rate_ok = success_rate >= 99

    print(f"\n  验收标准检查:")
    print(f"    P99 < 3000ms:     {' PASS' if p99_ok else ' FAIL'} ({sorted(latencies)[int(len(latencies)*0.99)]:.1f}ms)")
    print(f"    错误率 < 1%:      {' PASS' if rate_ok else ' FAIL'} ({100-success_rate:.1f}%)")
    print(f"    目标并发 {concurrency}: {' PASS' if p99_ok and rate_ok else ' FAIL'}")

    return p99_ok and rate_ok


def main():
    parser = argparse.ArgumentParser(description="压力测试工具")
    parser.add_argument("--concurrency", "-c", type=int, default=100, help="并发数 (默认: 100)")
    parser.add_argument("--requests", "-n", type=int, default=1000, help="总请求数 (默认: 1000)")
    args = parser.parse_args()

    print(f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标服务: {BASE_URL}")
    print(f"测试端点: {len(ENDPOINTS)} 个")

    try:
        ok = asyncio.run(run_stress_test(args.concurrency, args.requests))
        exit(0 if ok else 1)
    except KeyboardInterrupt:
        print("\n用户中断测试")
        exit(130)
    except Exception as e:
        print(f"\n测试执行失败: {e}")
        exit(1)


if __name__ == "__main__":
    main()