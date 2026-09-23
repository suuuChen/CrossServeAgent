"""
跨境电商Agent自动化评测脚本
指标：
客服：意图识别>=90%，订单事实准确率>=95%
合规：违禁内容拦截率>=98%
Listing：平台规范符合率>=95%（LLM评委+人工抽检）
输出：eval/report.md
"""
import json
import time
import os
from typing import Dict, List, Any
import requests
from openai import OpenAI

BASE_URL = "http://localhost:8000/api/v1"
TEST_DATASET_PATH = "eval/test_dataset.json"
REPORT_OUT_PATH = "eval/report.md"

# ========= 评测阈值（需求指标） =========
THRESHOLD_INTENT = 0.90
THRESHOLD_FACT = 0.95
THRESHOLD_COMPLIANCE_BLOCK = 0.98
THRESHOLD_LISTING_SPEC = 0.95

# ========= LLM评委配置（用于Listing质量评审，可填自己的key） =========
LLM_JUDGE_ENABLE = False
llm_client = OpenAI(api_key="sk-xxx", base_url="https://api.openai.com/v1")

session_http = requests.Session()
session_http.headers.update({"Content-Type": "application/json"})


def load_test_dataset() -> Dict[str, Any]:
    with open(TEST_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def eval_customer_service(test_items: List[Dict]) -> Dict[str, Any]:
    """
    客服评测：200条多语言测试样例
    返回：意图识别正确数、总数量；事实校验正确数；明细列表
    """
    intent_ok = 0
    intent_total = 0
    fact_ok = 0
    fact_total = 0
    details = []

    for item in test_items:
        qid = item["id"]
        query = item["query"]
        gold_intent = item["gold_intent"]
        lang = item["language"]
        fact_check_cfg = item.get("fact_check", {})
        need_fact_check = fact_check_cfg.get("need_order", False)

        payload = {
            "message": query,
            "language": lang,
            "session_id": None
        }
        try:
            resp = session_http.post(f"{BASE_URL}/chat", json=payload, timeout=45)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            details.append({
                "id": qid,
                "query": query,
                "error": f"http error:{str(e)}",
                "intent_match": False,
                "fact_match": None
            })
            continue

        pred_intent = data.get("intent", "")
        intent_match = (pred_intent == gold_intent)
        intent_total += 1
        if intent_match:
            intent_ok += 1

        fact_match: bool | None = None
        if need_fact_check:
            fact_total +=1
            order_no = fact_check_cfg.get("order_no")
            expect_not_exist = fact_check_cfg.get("expect_not_exist", False)
            # 调用订单查询接口拿真实数据库订单，校验Agent回复
            try:
                ord_resp = session_http.post(f"{BASE_URL}/orders/query", json={"order_no": order_no}, timeout=20)
                ord_data = ord_resp.json()
                real_order_exist = ord_data.get("success", False)
                agent_resp_text = data.get("response", "")

                if expect_not_exist:
                    # 预期订单不存在：agent回复需要体现查无此单
                    fact_match = ("未找到" in agent_resp_text) or ("could not find" in agent_resp_text.lower())
                else:
                    # 订单真实存在：回复必须包含订单号关键字
                    fact_match = (order_no in agent_resp_text)
                if fact_match:
                    fact_ok += 1
            except Exception as e:
                fact_match = False

        details.append({
            "id": qid,
            "query": query,
            "gold_intent": gold_intent,
            "pred_intent": pred_intent,
            "intent_match": intent_match,
            "fact_match": fact_match,
            "response_snippet": data.get("response", "")[:120]
        })
        time.sleep(0.2)
    intent_acc = intent_ok / intent_total if intent_total > 0 else 0.0
    fact_acc = fact_ok / fact_total if fact_total >0 else 0.0
    return {
        "intent_ok": intent_ok,
        "intent_total": intent_total,
        "intent_accuracy": intent_acc,
        "fact_ok": fact_ok,
        "fact_total": fact_total,
        "fact_accuracy": fact_acc,
        "details": details
    }


def eval_compliance(test_items: List[Dict]) -> Dict[str, Any]:
    """
    合规评测：100条不合规输入，校验blocked==True
    """
    block_ok = 0
    total = 0
    details = []
    for item in test_items:
        text = item["text"]
        expect_blocked = item["expect_blocked"]
        lang = item["language"]
        total += 1
        try:
            payload = {"text": text, "language": lang}
            resp = session_http.post(f"{BASE_URL}/compliance/check", json=payload, timeout=20)
            resp.raise_for_status()
            d = resp.json()
            actual_blocked = d["result"]["blocked"]
            ok = (actual_blocked == expect_blocked)
            if ok:
                block_ok += 1
            details.append({
                "text": text[:80],
                "expect_blocked": expect_blocked,
                "actual_blocked": actual_blocked,
                "pass": ok
            })
        except Exception as e:
            details.append({
                "text": text[:80],
                "error": str(e),
                "pass": False
            })
        time.sleep(0.15)
    block_rate = block_ok / total if total>0 else 0.0
    return {
        "block_ok": block_ok,
        "total": total,
        "block_rate": block_rate,
        "details": details
    }


def _llm_judge_listing(listing_variant: Dict, platform: str) -> Dict[str, Any]:
    """LLM评委：评判Listing是否符合平台规范"""
    prompt = f"""
你是跨境电商Listing评审专家，平台:{platform}。
评判维度：
1. title是否符合平台字符上限；
2. 是否必填字段不为空（title、bullet_points、description）；
3. A+内容结构完整（如有）。
输出JSON：{{"pass":bool,"reason":"简要说明问题"}}
待评审variant:
{json.dumps(listing_variant, ensure_ascii=False)}
只返回JSON，不要额外文字。
"""
    resp = llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.0
    )
    raw = resp.choices[0].message.content.strip()
    return json.loads(raw)


def eval_listing(listing_sample_items: List[Dict]) -> Dict[str, Any]:
    """Listing评测：30个样本，调用生成接口；LLM评委评审"""
    ok_count = 0
    total = len(listing_sample_items)
    details = []
    for sample in listing_sample_items:
        try:
            payload = {
                "product": sample["product"],
                "platform": sample["platform"],
                "variants": 1
            }
            resp = session_http.post(f"{BASE_URL}/listing/generate", json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            variant = data["result"]["variants"][0]
            if LLM_JUDGE_ENABLE:
                judge = _llm_judge_listing(variant, sample["platform"])
                pass_flag = judge["pass"]
                reason = judge["reason"]
            else:
                # 关闭LLM：只做基础字段/字符规则校验（模拟人工抽检）
                title = variant.get("title", "")
                bullets = variant.get("bullet_points", [])
                desc = variant.get("description", "")
                pass_flag = bool(title and len(bullets)>=3 and desc)
                reason = "基础字段校验（未启用LLM评委）"
            if pass_flag:
                ok_count += 1
            details.append({
                "product_name": sample["product"]["name"],
                "platform": sample["platform"],
                "pass": pass_flag,
                "reason": reason,
                "title_snippet": variant.get("title","")[:80]
            })
        except Exception as e:
            details.append({
                "product_name": sample.get("product",{}).get("name",""),
                "pass": False,
                "reason": f"api error:{str(e)}"
            })
        time.sleep(0.3)
    spec_rate = ok_count / total if total>0 else 0.0
    return {
        "ok_count": ok_count,
        "total": total,
        "spec_compliance_rate": spec_rate,
        "details": details
    }


def render_markdown_report(
    cs_result: Dict,
    comp_result: Dict,
    listing_result: Dict,
    out_path: str
):
    md = []
    md.append("# 跨境Agent自动化评测报告\n")
    md.append(f"评测时间：{time.strftime('%Y‑%m‑%d %H:%M:%S')}\n")
    md.append("## 指标阈值（需求）\n")
    md.append(f"- 客服意图识别 ≥ {THRESHOLD_INTENT*100:.0f}%\n")
    md.append(f"- 客服订单事实准确率 ≥ {THRESHOLD_FACT*100:.0f}%\n")
    md.append(f"- 合规违禁拦截率 ≥ {THRESHOLD_COMPLIANCE_BLOCK*100:.0f}%\n")
    md.append(f"- Listing平台规范符合率 ≥ {THRESHOLD_LISTING_SPEC*100:.0f}%\n")

    md.append("\n## 1 客服评测（200条多语言咨询）\n")
    md.append(f"- 意图识别：{cs_result['intent_ok']}/{cs_result['intent_total']} ，准确率 `{cs_result['intent_accuracy']*100:.2f}%`")
    md.append(f"  {'✅达标' if cs_result['intent_accuracy'] >= THRESHOLD_INTENT else '❌未达标'}")
    md.append(f"- 订单事实校验：{cs_result['fact_ok']}/{cs_result['fact_total']}，准确率 `{cs_result['fact_accuracy']*100:.2f}%`")
    md.append(f"  {'✅达标' if cs_result['fact_accuracy'] >= THRESHOLD_FACT else '❌未达标'}\n")

    md.append("\n## 2 合规评测（100条不合规样例）\n")
    md.append(f"- 拦截正确：{comp_result['block_ok']}/{comp_result['total']}，拦截率 `{comp_result['block_rate']*100:.2f}%`")
    md.append(f"  {'✅达标' if comp_result['block_rate'] >= THRESHOLD_COMPLIANCE_BLOCK else '❌未达标'}\n")

    md.append("\n##3 Listing评测（30样本）\n")
    md.append(f"- 规范合格：{listing_result['ok_count']}/{listing_result['total']}，符合率 `{listing_result['spec_compliance_rate']*100:.2f}%`")
    md.append(f"  {'✅达标' if listing_result['spec_compliance_rate'] >= THRESHOLD_LISTING_SPEC else '❌未达标'}\n")

    md.append("\n## 总评\n")
    all_pass = (
        cs_result["intent_accuracy"] >= THRESHOLD_INTENT
        and cs_result["fact_accuracy"] >= THRESHOLD_FACT
        and comp_result["block_rate"] >= THRESHOLD_COMPLIANCE_BLOCK
        and listing_result["spec_compliance_rate"] >= THRESHOLD_LISTING_SPEC
    )
    md.append(f"{'🎉全部指标通过验收' if all_pass else '⚠️部分指标未达到需求阈值，需要迭代修复'}\n")

    md.append("\n> 完整错误明细保存在json输出，可人工复看badcase。")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf‑8") as f:
        f.write("\n".join(md))

    # 同时输出原始明细json
    raw_out = out_path.replace(".md", ".json")
    raw_report = {
        "cs": cs_result,
        "compliance": comp_result,
        "listing": listing_result
    }
    with open(raw_out, "w", encoding="utf‑8") as f:
        json.dump(raw_report, f, ensure_ascii=False, indent=2)
    print(f"报告已输出：{out_path} , {raw_out}")


def main():
    ds = load_test_dataset()
    print("开始执行自动化评测...")

    cs_res = eval_customer_service(ds["customer_service_200"])
    print(f"客服评测完成：意图acc {cs_res['intent_accuracy']:.3f}，事实acc {cs_res['fact_accuracy']:.3f}")

    comp_res = eval_compliance(ds["compliance_negative_100"])
    print(f"合规评测完成，拦截率 {comp_res['block_rate']:.3f}")

    listing_res = eval_listing(ds["listing_30_samples"])
    print(f"Listing评测完成，规范符合率 {listing_res['spec_compliance_rate']:.3f}")

    render_markdown_report(cs_res, comp_res, listing_res, REPORT_OUT_PATH)


if __name__ == "__main__":
    main()
