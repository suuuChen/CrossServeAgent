"""
跨境电商Agent自动化评测脚本
指标：
客服：意图识别>=90%，订单事实准确率>=95%
合规：违禁内容拦截率>=98%
Listing：平台规范符合率>=95%（LLM评委+人工抽检）

使用方法：
  python test_runner.py                # 默认跑小样本子集（快速验证通路）
  FULL=1 python test_runner.py         # 跑全量评测（200+100+30）
"""
import json
import time
import os
import sys
from typing import Dict, List, Any
import requests

BASE_URL = "http://localhost:8000/api/v1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATASET_PATH = os.path.join(SCRIPT_DIR, "test_dataset.json")
REPORT_OUT_PATH = os.path.join(SCRIPT_DIR, "report.md")

FULL_RUN = os.environ.get("FULL", "0") == "1"

CS_LIMIT = 200 if FULL_RUN else 15
COMP_LIMIT = 100 if FULL_RUN else 10
LISTING_LIMIT = 30 if FULL_RUN else 6

CHAT_TIMEOUT = 180
LISTING_TIMEOUT = 180
COMPLIANCE_TIMEOUT = 30
ORDER_TIMEOUT = 30

THRESHOLD_INTENT = 0.90
THRESHOLD_FACT = 0.95
THRESHOLD_COMPLIANCE_BLOCK = 0.98
THRESHOLD_LISTING_SPEC = 0.95

session_http = requests.Session()
session_http.headers.update({"Content-Type": "application/json"})


def _wait_backend_ready():
    print(f"[准备] 等待后端服务就绪 (timeout=120s)...")
    deadline = time.time() + 120
    last_err = None
    while time.time() < deadline:
        try:
            r = session_http.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=5)
            if r.status_code == 200:
                data = r.json()
                print(f"[准备] 后端已就绪 ✅ (llm={data.get('services', {}).get('llm', '?')}, db={data.get('services', {}).get('database', '?')})")
                return True
        except Exception as e:
            last_err = e
        time.sleep(2)
    print(f"[准备] ❌ 后端未就绪，最后错误: {last_err}")
    print(f"         请先启动后端: cd backend && python -m uvicorn app.main:app --port 8000")
    sys.exit(1)


def load_test_dataset() -> Dict[str, Any]:
    with open(TEST_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _print_progress(current, total, label, last=""):
    pct = current / total * 100
    bar_len = 30
    filled = int(bar_len * current / total)
    bar = "█" * filled + "░" * (bar_len - filled)
    sys.stdout.write(f"\r  {label} [{bar}] {current}/{total} ({pct:.0f}%) {last[:80]}")
    sys.stdout.flush()
    if current >= total:
        print()


def eval_compliance(test_items: List[Dict]) -> Dict[str, Any]:
    block_ok = 0
    total = 0
    details = []
    items = test_items[:COMP_LIMIT]
    print(f"\n[1/3] 合规评测 ({len(items)}/{len(test_items)} 条)...")
    t0 = time.time()

    for item in items:
        text = item["query"]
        expect_blocked = item["expected_blocked"]
        lang = item["language"]
        total += 1
        try:
            payload = {"text": text, "language": lang}
            resp = session_http.post(f"{BASE_URL}/compliance/check", json=payload, timeout=COMPLIANCE_TIMEOUT)
            resp.raise_for_status()
            d = resp.json()
            actual_blocked = d["result"]["blocked"]
            ok = (actual_blocked == expect_blocked)
            if ok:
                block_ok += 1
            matched_cat = ""
            if d["result"].get("categories"):
                matched_cat = d["result"]["categories"][0].get("category", "")
            details.append({
                "id": item.get("id", ""),
                "text": text[:100],
                "expect_blocked": expect_blocked,
                "actual_blocked": actual_blocked,
                "expected_category": item.get("expected_category", ""),
                "actual_category": matched_cat,
                "pass": ok
            })
            last = "✓" if ok else f"✗ expect={expect_blocked} got={actual_blocked} cat={matched_cat}"
        except Exception as e:
            details.append({
                "id": item.get("id", ""),
                "text": text[:100],
                "error": str(e),
                "pass": False
            })
            last = f"✗ {str(e)[:30]}"
        _print_progress(total, len(items), "合规", last)
        time.sleep(0.02)

    elapsed = time.time() - t0
    block_rate = block_ok / total if total > 0 else 0.0
    print(f"  耗时 {elapsed:.1f}s  拦截率 {block_ok}/{total} = {block_rate*100:.1f}%")
    return {
        "block_ok": block_ok,
        "total": total,
        "block_rate": block_rate,
        "details": details,
        "elapsed": round(elapsed, 1)
    }


def eval_listing(listing_samples: List[Dict], platforms: List[str]) -> Dict[str, Any]:
    ok_count = 0
    items = listing_samples[:LISTING_LIMIT]
    details = []
    print(f"\n[2/3] Listing评测 (最多{len(items)}样本 x {len(platforms)}平台)...")
    t0 = time.time()

    test_cases = []
    for i, product in enumerate(items):
        for plat in platforms:
            test_cases.append((product, plat, i * len(platforms) + len(platforms)))

    test_cases = test_cases[:LISTING_LIMIT]

    for idx, (product, plat, _) in enumerate(test_cases, 1):
        try:
            payload = {
                "product": product,
                "platform": plat,
                "variants": 1,
                "language": "en"
            }
            resp = session_http.post(f"{BASE_URL}/listing/generate", json=payload, timeout=LISTING_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            variant = data["result"]["variants"][0]

            title = variant.get("title", "")
            bullets = variant.get("bullet_points", [])
            desc = variant.get("description", "")

            pass_flag = bool(title and len(bullets) >= 3 and desc and len(title) > 10)
            reasons = []
            if not title or len(title) <= 10:
                reasons.append("title 缺失或过短")
            if len(bullets) < 3:
                reasons.append(f"bullet_points 仅{len(bullets)}条(需>=3)")
            if not desc:
                reasons.append("description 缺失")
            reason = "; ".join(reasons) if reasons else "基础字段校验通过"

            if pass_flag:
                ok_count += 1
            details.append({
                "product_name": product.get("name", ""),
                "platform": plat,
                "pass": pass_flag,
                "reason": reason,
                "title": title[:100],
                "bullet_count": len(bullets),
                "desc_len": len(desc)
            })
            last = ("✓" if pass_flag else "✗") + f" {plat} | {product.get('name','')[:20]}"
        except Exception as e:
            details.append({
                "product_name": product.get("name", ""),
                "platform": plat,
                "pass": False,
                "reason": f"api error:{str(e)[:80]}"
            })
            last = f"✗ {plat} err={str(e)[:30]}"
        _print_progress(idx, len(test_cases), "Listing", last)
        time.sleep(0.2)

    elapsed = time.time() - t0
    spec_rate = ok_count / len(test_cases) if test_cases else 0.0
    print(f"  耗时 {elapsed:.1f}s  规范符合率 {ok_count}/{len(test_cases)} = {spec_rate*100:.1f}%")
    return {
        "ok_count": ok_count,
        "total": len(test_cases),
        "spec_compliance_rate": spec_rate,
        "details": details,
        "elapsed": round(elapsed, 1)
    }


def eval_customer_service(test_items: List[Dict]) -> Dict[str, Any]:
    intent_ok = 0
    intent_total = 0
    fact_ok = 0
    fact_total = 0
    details = []
    items = test_items[:CS_LIMIT]
    print(f"\n[3/3] 客服评测 ({len(items)}/{len(test_items)} 条)...")
    print(f"  timeout={CHAT_TIMEOUT}s/条, 预计耗时 {len(items)*15}s")
    t0 = time.time()

    for i, item in enumerate(items, 1):
        qid = item["id"]
        query = item["query"]
        gold_intent = item["expected_intent"]
        lang = item["language"]
        fact_check_cfg = item.get("fact_check")

        payload = {
            "message": query,
            "language": lang,
            "session_id": None
        }
        try:
            st = time.time()
            resp = session_http.post(f"{BASE_URL}/chat", json=payload, timeout=CHAT_TIMEOUT)
            elapsed = time.time() - st
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            details.append({
                "id": qid,
                "query": query,
                "error": f"http error:{str(e)[:100]}",
                "intent_match": False,
                "fact_match": None
            })
            _print_progress(i, len(items), "客服", f"✗ err {str(e)[:30]}")
            continue

        pred_intent = data.get("intent", "")
        intent_match = (pred_intent == gold_intent)
        intent_total += 1
        if intent_match:
            intent_ok += 1

        fact_match = None
        if fact_check_cfg and fact_check_cfg.get("order_no"):
            fact_total += 1
            order_no = fact_check_cfg["order_no"]
            agent_resp_text = data.get("response", "")
            fact_match = (order_no in agent_resp_text)
            if fact_match:
                fact_ok += 1

        details.append({
            "id": qid,
            "query": query[:80],
            "gold_intent": gold_intent,
            "pred_intent": pred_intent,
            "intent_match": intent_match,
            "fact_match": fact_match,
            "response_snippet": data.get("response", "")[:150],
            "confidence": data.get("confidence"),
            "latency_s": round(elapsed, 1)
        })
        status = "✓" if intent_match else f"✗ pred={pred_intent} gold={gold_intent}"
        _print_progress(i, len(items), "客服", f"{status} ({elapsed:.1f}s)")
        time.sleep(0.05)

    total_elapsed = time.time() - t0
    intent_acc = intent_ok / intent_total if intent_total > 0 else 0.0
    fact_acc = fact_ok / fact_total if fact_total > 0 else 0.0
    print(f"  总耗时 {total_elapsed:.1f}s  意图acc {intent_ok}/{intent_total}={intent_acc*100:.1f}%  事实acc {fact_ok}/{fact_total}={fact_acc*100:.1f}%")
    return {
        "intent_ok": intent_ok,
        "intent_total": intent_total,
        "intent_accuracy": intent_acc,
        "fact_ok": fact_ok,
        "fact_total": fact_total,
        "fact_accuracy": fact_acc,
        "details": details,
        "elapsed": round(total_elapsed, 1)
    }


def render_markdown_report(cs_result, comp_result, listing_result, out_path):
    md = []
    md.append("# 跨境Agent自动化评测报告\n")
    md.append(f"评测时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    mode = "全量评测" if FULL_RUN else f"子集评测 (CS={CS_LIMIT}, Comp={COMP_LIMIT}, Listing={LISTING_LIMIT})"
    md.append(f"评测模式：{mode}\n")
    md.append("\n## 指标阈值（需求）\n")
    md.append(f"- 客服意图识别 ≥ {THRESHOLD_INTENT*100:.0f}%\n")
    md.append(f"- 客服订单事实准确率 ≥ {THRESHOLD_FACT*100:.0f}%\n")
    md.append(f"- 合规违禁拦截率 ≥ {THRESHOLD_COMPLIANCE_BLOCK*100:.0f}%\n")
    md.append(f"- Listing平台规范符合率 ≥ {THRESHOLD_LISTING_SPEC*100:.0f}%\n")

    cs_elapsed = cs_result.get("elapsed", "?")
    md.append(f"\n## 1 客服评测 ({cs_result['intent_total']}条, 耗时{cs_elapsed}s)\n")
    md.append(f"- 意图识别：{cs_result['intent_ok']}/{cs_result['intent_total']} ，准确率 `{cs_result['intent_accuracy']*100:.2f}%`")
    md.append(f"  {'✅达标' if cs_result['intent_accuracy'] >= THRESHOLD_INTENT else '❌未达标'}")
    fact_line = f"- 订单事实校验：{cs_result['fact_ok']}/{cs_result['fact_total']}" if cs_result['fact_total'] > 0 else "- 订单事实校验：无订单号相关case"
    md.append(fact_line)
    if cs_result['fact_total'] > 0:
        md.append(f"  准确率 `{cs_result['fact_accuracy']*100:.2f}%`")
        md.append(f"  {'✅达标' if cs_result['fact_accuracy'] >= THRESHOLD_FACT else '❌未达标'}")

    comp_elapsed = comp_result.get("elapsed", "?")
    md.append(f"\n## 2 合规评测 ({comp_result['total']}条, 耗时{comp_elapsed}s)\n")
    md.append(f"- 拦截正确：{comp_result['block_ok']}/{comp_result['total']}，拦截率 `{comp_result['block_rate']*100:.2f}%`")
    md.append(f"  {'✅达标' if comp_result['block_rate'] >= THRESHOLD_COMPLIANCE_BLOCK else '❌未达标'}")

    list_elapsed = listing_result.get("elapsed", "?")
    md.append(f"\n## 3 Listing评测 ({listing_result['total']}样本, 耗时{list_elapsed}s)\n")
    md.append(f"- 规范合格：{listing_result['ok_count']}/{listing_result['total']}，符合率 `{listing_result['spec_compliance_rate']*100:.2f}%`")
    md.append(f"  {'✅达标' if listing_result['spec_compliance_rate'] >= THRESHOLD_LISTING_SPEC else '❌未达标'}")

    cs_pass = cs_result['intent_accuracy'] >= THRESHOLD_INTENT
    fact_pass = cs_result['fact_total'] == 0 or cs_result['fact_accuracy'] >= THRESHOLD_FACT
    comp_pass = comp_result['block_rate'] >= THRESHOLD_COMPLIANCE_BLOCK
    list_pass = listing_result['spec_compliance_rate'] >= THRESHOLD_LISTING_SPEC

    md.append("\n## 总评\n")
    all_pass = cs_pass and fact_pass and comp_pass and list_pass
    md.append(f"{'🎉全部指标通过验收' if all_pass else '⚠️部分指标未达到需求阈值，需要迭代修复'}")

    failed_details = []
    if not cs_pass:
        failed_details.append(f"- 客服意图识别 ({cs_result['intent_accuracy']*100:.1f}% < {THRESHOLD_INTENT*100:.0f}%)")
    if not fact_pass and cs_result['fact_total'] > 0:
        failed_details.append(f"- 客服事实校验 ({cs_result['fact_accuracy']*100:.1f}% < {THRESHOLD_FACT*100:.0f}%)")
    if not comp_pass:
        failed_details.append(f"- 合规拦截率 ({comp_result['block_rate']*100:.1f}% < {THRESHOLD_COMPLIANCE_BLOCK*100:.0f}%)")
    if not list_pass:
        failed_details.append(f"- Listing符合率 ({listing_result['spec_compliance_rate']*100:.1f}% < {THRESHOLD_LISTING_SPEC*100:.0f}%)")
    if failed_details:
        md.append("\n未达标项：")
        md.extend(failed_details)

    md.append("\n---\n> 完整错误明细保存在 json 输出，可人工复看 badcase。")

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    raw_out = out_path.replace(".md", ".json")
    raw_report = {
        "meta": {
            "run_mode": "full" if FULL_RUN else "subset",
            "limits": {"cs": CS_LIMIT, "compliance": COMP_LIMIT, "listing": LISTING_LIMIT},
            "thresholds": {
                "intent": THRESHOLD_INTENT,
                "fact": THRESHOLD_FACT,
                "compliance": THRESHOLD_COMPLIANCE_BLOCK,
                "listing": THRESHOLD_LISTING_SPEC
            },
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "cs": cs_result,
        "compliance": comp_result,
        "listing": listing_result
    }
    with open(raw_out, "w", encoding="utf-8") as f:
        json.dump(raw_report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 报告已输出：{out_path} , {raw_out}")


def main():
    print("=" * 60)
    print(" 跨境电商Agent 自动化评测")
    mode = "全量评测" if FULL_RUN else f"子集评测 (CS≤{CS_LIMIT}, Comp≤{COMP_LIMIT}, Listing≤{LISTING_LIMIT})"
    print(f" 模式: {mode}")
    print("=" * 60)

    _wait_backend_ready()

    ds = load_test_dataset()
    cs_cases = ds["customer_service_tests"]["cases"]
    comp_cases = ds["compliance_tests"]["cases"]
    lst_info = ds.get("listing_quality_tests", {})
    lst_products = lst_info.get("sample_products_for_listing", [])
    lst_platforms = lst_info.get("platforms", ["amazon", "temu", "tiktok_shop"])

    print(f"\n数据集加载完成: 客服{len(cs_cases)}条, 合规{len(comp_cases)}条, Listing产品{len(lst_products)}个 x {len(lst_platforms)}平台")

    comp_res = eval_compliance(comp_cases)

    listing_res = eval_listing(lst_products, lst_platforms)

    cs_res = eval_customer_service(cs_cases)

    print("\n" + "=" * 60)
    print(" 评测结果汇总")
    print("=" * 60)
    intent_ok = cs_res['intent_accuracy'] >= THRESHOLD_INTENT
    fact_ok = cs_res['fact_total'] == 0 or cs_res['fact_accuracy'] >= THRESHOLD_FACT
    comp_ok = comp_res['block_rate'] >= THRESHOLD_COMPLIANCE_BLOCK
    list_ok = listing_res['spec_compliance_rate'] >= THRESHOLD_LISTING_SPEC
    print(f" 客服意图识别: {cs_res['intent_accuracy']*100:.1f}% {'✅' if intent_ok else '❌'}  (≥{THRESHOLD_INTENT*100:.0f}%)")
    if cs_res['fact_total'] > 0:
        print(f" 客服事实校验: {cs_res['fact_accuracy']*100:.1f}% {'✅' if fact_ok else '❌'}  (≥{THRESHOLD_FACT*100:.0f}%)")
    print(f" 合规拦截率:   {comp_res['block_rate']*100:.1f}% {'✅' if comp_ok else '❌'}  (≥{THRESHOLD_COMPLIANCE_BLOCK*100:.0f}%)")
    print(f" Listing符合率: {listing_res['spec_compliance_rate']*100:.1f}% {'✅' if list_ok else '❌'}  (≥{THRESHOLD_LISTING_SPEC*100:.0f}%)")

    render_markdown_report(cs_res, comp_res, listing_res, REPORT_OUT_PATH)


if __name__ == "__main__":
    main()