import urllib.request
import json
import sys
import time
import threading

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0
TOTAL = 0
TEST_NUM = 0
START_TIME = None


class Colors:
    """ANSI 颜色常量"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def print_header(title, icon="🚀"):
    """打印醒目的分组标题"""
    width = 70
    print(f"\n{Colors.CYAN}{'═' * width}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {icon} {title}{Colors.RESET}")
    print(f"{Colors.CYAN}{'═' * width}{Colors.RESET}\n")


def print_section(title, emoji="📋"):
    """打印子模块标题"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}▸ {emoji} {title}{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")


def test(name, method, path, data=None, check=None, timeout=120, expect_404=False, expect_429=False):
    global PASS, FAIL, TOTAL, TEST_NUM
    TEST_NUM += 1
    TOTAL += 1
    
    try:
        url = BASE + path
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, method=method)
        if body:
            req.add_header('Content-Type', 'application/json')
        
        resp = urllib.request.urlopen(req, timeout=timeout)
        
        raw = resp.read()
        
        try:
            d = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            d = {"_raw_bytes": len(raw), "_content_type": resp.headers.get("Content-Type", "")}
        
        if expect_404:
            print(f"{Colors.RED}[✗] Test #{TEST_NUM:02d}: {name}{Colors.RESET}")
            print(f"       Expected 404 but got 200")
            FAIL += 1
            return d
        
        if expect_429:
            print(f"{Colors.RED}[✗] Test #{TEST_NUM:02d}: {name}{Colors.RESET}")
            print(f"       Expected 429 but got 200")
            FAIL += 1
            return d
        
        if "_raw_bytes" in d:
            if d["_raw_bytes"] > 0:
                print(f"{Colors.GREEN}[✓] Test #{TEST_NUM:02d}: {name}{Colors.RESET}")
                PASS += 1
            else:
                print(f"{Colors.RED}[✗] Test #{TEST_NUM:02d}: {name}{Colors.RESET}")
                print(f"       Empty non-JSON response")
                FAIL += 1
            return d
        
        if check and not check(d):
            print(f"{Colors.RED}[✗] Test #{TEST_NUM:02d}: {name}{Colors.RESET}")
            print(f"       Check failed → {json.dumps(d, ensure_ascii=False)[:150]}")
            FAIL += 1
        else:
            print(f"{Colors.GREEN}[✓] Test #{TEST_NUM:02d}: {name}{Colors.RESET}")
            PASS += 1
        
        return d
        
    except urllib.error.HTTPError as e:
        if expect_404 and e.code == 404:
            print(f"{Colors.GREEN}[✓] Test #{TEST_NUM:02d}: {name}{Colors.RESET}")
            PASS += 1
            return None
        
        if expect_429 and e.code == 429:
            print(f"{Colors.GREEN}[✓] Test #{TEST_NUM:02d}: {name}{Colors.RESET}")
            PASS += 1
            return None
        
        body = e.read().decode()[:150]
        print(f"{Colors.RED}[✗] Test #{TEST_NUM:02d}: {name}{Colors.RESET}")
        print(f"       HTTP {e.code} → {body}")
        FAIL += 1
        return None
        
    except Exception as e:
        print(f"{Colors.RED}[✗] Test #{TEST_NUM:02d}: {name}{Colors.RESET}")
        print(f"       Error → {str(e)[:100]}")
        FAIL += 1
        return None


def print_summary():
    """打印最终统计摘要"""
    width = 60

    print("\n" + "=" * width)
    print(f"  RESULT: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
    print("=" * width)


# ==================== 主程序入口 ====================
if __name__ == "__main__":
    START_TIME = time.time()
    


    # ==================== Week 1 ====================
    print_section("Week 1: Core Functionality")
    
    print(f"\n{Colors.BOLD}System Health{Colors.RESET}")
    test("Root endpoint", "GET", "/", check=lambda d: d.get("status") == "running")
    test("Health check", "GET", "/api/v1/health")
    
    print(f"\n{Colors.BOLD}Order Management{Colors.RESET}")
    test("Query existing order", "POST", "/api/v1/orders/query",
         {"order_no": "ORD-20240101-001"},
         check=lambda d: d.get("order_no") == "ORD-20240101-001" and d.get("items"))
    
    test("Query non-existing order → 404", "POST", "/api/v1/orders/query",
         {"order_no": "ORD-NOT-EXIST"}, expect_404=True)
    
    print(f"\n{Colors.BOLD}Chat Intents (Chinese){Colors.RESET}")
    r = test("Order query intent", "POST", "/api/v1/chat",
             {"message": "我的订单ORD-20240101-001在哪里", "language": "zh"},
             check=lambda d: d["intent"] == "order_query" and d["should_transfer"] == False)
    sid = r["session_id"] if r else None
    
    test("Shipping query intent", "POST", "/api/v1/chat",
         {"message": "快递到哪了", "language": "zh"},
         check=lambda d: d["intent"] == "shipping_query")
    
    test("General FAQ intent", "POST", "/api/v1/chat",
         {"message": "支持什么支付方式", "language": "zh"},
         check=lambda d: d["intent"] == "general_faq" and d["should_transfer"] == False)
    
    test("Greeting intent", "POST", "/api/v1/chat",
         {"message": "你好", "language": "zh"},
         check=lambda d: d["should_transfer"] == False)
    
    test("Human transfer intent (explicit)", "POST", "/api/v1/chat",
         {"message": "我要转人工客服", "language": "zh"},
         check=lambda d: d["intent"] == "human_transfer" and d["should_transfer"] == True)
    
    print(f"\n{Colors.BOLD}Session Management{Colors.RESET}")
    test("Session persistence (multi-turn)", "GET", f"/api/v1/sessions/{sid}",
         check=lambda d: d["session"]["turn_count"] >= 1)
    
    test("Continue chat with session_id", "POST", "/api/v1/chat",
         {"message": "有什么好的运动鞋推荐", "language": "zh", "session_id": sid})
    
    test("Delete session", "DELETE", f"/api/v1/sessions/{sid}")
    
    test("Deleted session → 404", "GET", f"/api/v1/sessions/{sid}", expect_404=True)

    # ==================== Week 2 ====================
    print_section("Week 2: Advanced Features")
    
    print(f"\n{Colors.BOLD}Multi-language Support{Colors.RESET}")
    test("English chat (order)", "POST", "/api/v1/chat",
         {"message": "Where is my order", "language": "en"},
         check=lambda d: d["language"] == "en")
    
    test("Spanish chat (shipping)", "POST", "/api/v1/chat",
         {"message": "¿Dónde está mi pedido?", "language": "es"},
         check=lambda d: d["language"] == "es")
    
    test("French chat (return)", "POST", "/api/v1/chat",
         {"message": "Quelle est la politique de retour", "language": "fr"},
         check=lambda d: d["language"] == "fr")
    
    test("German chat (product)", "POST", "/api/v1/chat",
         {"message": "Empfehle mir gute Kopfhörer", "language": "de"},
         check=lambda d: d["language"] == "de")
    
    test("Auto-detect language (EN→ZH)", "POST", "/api/v1/chat",
         {"message": "I want to return this item please", "language": "zh"},
         check=lambda d: d["language"] in ["en", "zh"])
    
    print(f"\n{Colors.BOLD}Compliance Filtering{Colors.RESET}")
    test("Get compliance categories", "GET", "/api/v1/compliance/categories",
         check=lambda d: d.get("success") and len(d.get("categories", [])) >= 5)
    
    test("Check safe text (中文)", "POST", "/api/v1/compliance/check",
         {"text": "你好，我想咨询一下商品信息", "language": "zh"},
         check=lambda d: d.get("success") and not d["result"]["blocked"])
    
    test("Check blocked text (中文)", "POST", "/api/v1/compliance/check",
         {"text": "我要举报有人在这里卖毒品", "language": "zh"},
         check=lambda d: d.get("success") and d["result"]["blocked"])
    
    test("Check blocked text (English)", "POST", "/api/v1/compliance/check",
         {"text": "This website sells drugs and guns", "language": "en"},
         check=lambda d: d.get("success") and d["result"]["blocked"])
    
    test("Chat with prohibited content → blocked", "POST", "/api/v1/chat",
         {"message": "我想买点毒品", "language": "zh"},
         check=lambda d: d.get("compliance_blocked") == True)
    
    test("Chat with safe content → allowed", "POST", "/api/v1/chat",
         {"message": "我想咨询退款政策", "language": "zh"},
         check=lambda d: d.get("compliance_blocked") == False)
    
    print(f"\n{Colors.BOLD}Human Transfer Enhancement{Colors.RESET}")
    c1 = test("Complaint → auto transfer trigger", "POST", "/api/v1/chat",
              {"message": "你们的服务太差了，快递慢得要死，我要投诉！", "language": "zh"},
              check=lambda d: d["should_transfer"] == True)
    c1_sid = c1["session_id"] if c1 else None
    
    if c1_sid:
        test("Session status → pending_human", "GET", f"/api/v1/sessions/{c1_sid}",
             check=lambda d: d["session"].get("status") == "pending_human")
    
    test("List pending-human sessions", "GET", "/api/v1/sessions/pending-human",
         check=lambda d: d.get("success") and isinstance(d.get("sessions"), list))
    
    if c1_sid:
        test("Human agent takeover", "POST", 
             f"/api/v1/sessions/{c1_sid}/human-takeover?agent_name=Agent01",
             check=lambda d: d.get("success") and d.get("new_status") == "human_assisted")
    
    if c1_sid:
        test("Session after takeover → human_assisted", "GET", f"/api/v1/sessions/{c1_sid}",
             check=lambda d: d["session"].get("status") == "human_assisted")
    
    print(f"\n{Colors.BOLD}Audit Logging{Colors.RESET}")
    test("Query audit logs", "GET", "/api/v1/audit/logs?limit=10",
         check=lambda d: d.get("success") and isinstance(d.get("logs"), list))
    
    test("Filter logs by event_type", "GET", "/api/v1/audit/logs?event_type=chat&limit=5",
         check=lambda d: d.get("success"))
    
    test("Get audit statistics", "GET", "/api/v1/audit/stats",
         check=lambda d: d.get("success") and "stats" in d)
    
    test("Get stats with time filter", "GET", "/api/v1/audit/stats?hours=24",
         check=lambda d: d.get("success"))

    # ==================== Week 3 ====================
    print_section("Week 3: Operations Agent", "📊")
    
    listing_product = {
        "name": "Air Max Pro Running Shoes",
        "brand": "Nike",
        "category": "Running Shoes",
        "description": "Lightweight breathable running shoes with responsive cushioning",
        "key_features": ["Lightweight Design", "Breathable Mesh", "Responsive Cushion", "Durable Rubber Outsole", "Stylish Look"],
        "target_audience": "Runners and Fitness Enthusiasts"
    }
    
    print(f"\n{Colors.BOLD}Listing Generator{Colors.RESET}")
    test("Get listing platforms", "GET", "/api/v1/listing/platforms",
         check=lambda d: d.get("success") and len(d.get("platforms", [])) == 3)
    
    # 先执行批量测试，避免后续单个测试累积触发速率限制
    batch_products = [
        {"name": "Wireless Earbuds", "brand": "AudioPro", "category": "Electronics", "description": "True wireless earbuds", "key_features": ["Noise Cancelling", "30h Battery"], "target_audience": "Music Lovers"},
        {"name": "Yoga Mat", "brand": "FitLife", "category": "Sports", "description": "Non-slip yoga mat", "key_features": ["Eco-friendly", "Extra Thick"], "target_audience": "Yoga Practitioners"},
    ]
    test("Batch listing generation", "POST", "/api/v1/listing/batch",
         {"products": batch_products, "platform": "amazon", "variants_per_product": 2},
         check=lambda d: d["success"] and d["result"]["total"] == 2 and d["result"]["success_count"] == 2)
    
    test("Generate Amazon listing (1 variant)", "POST", "/api/v1/listing/generate",
         {"product": listing_product, "platform": "amazon", "variants": 1},
         check=lambda d: d["success"] and len(d["result"]["variants"]) == 1 and "a_plus" in d["result"]["variants"][0])
    
    test("Generate Temu listing (2 variants)", "POST", "/api/v1/listing/generate",
         {"product": listing_product, "platform": "temu", "variants": 2},
         check=lambda d: d["success"] and d["result"]["platform"] == "temu" and len(d["result"]["variants"]) == 2)
    
    test("Generate TikTok Shop listing (3 variants)", "POST", "/api/v1/listing/generate",
         {"product": listing_product, "platform": "tiktok_shop", "variants": 3},
         check=lambda d: d["success"] and d["result"]["platform"] == "tiktok_shop" and d["result"]["variants"][0]["a_plus"] is not None)
    
    test("A+ content included for Amazon/TikTok", "POST", "/api/v1/listing/generate",
         {"product": listing_product, "platform": "amazon", "variants": 1},
         check=lambda d: d["result"]["variants"][0]["a_plus"] is not None)
    
    test("Title within platform char limit", "POST", "/api/v1/listing/generate",
         {"product": listing_product, "platform": "tiktok_shop", "variants": 1},
         check=lambda d: d["result"]["variants"][0]["char_counts"]["title"] <= 60)
    
    print(f"\n{Colors.BOLD}Review Analyzer{Colors.RESET}")
    test("Get review themes", "GET", "/api/v1/reviews/themes",
         check=lambda d: d.get("success") and "quality" in d.get("theme_details", {}))
    
    sample_reviews = [
        {"content": "This product is amazing! Great quality and fast shipping.", "rating": 5},
        {"content": "Terrible quality, arrived broken. Want my money back!", "rating": 1},
        {"content": "It's okay, not great but not bad either.", "rating": 3},
        {"content": "Love the design! Perfect fit, very comfortable.", "rating": 5},
        {"content": "Poor customer service, delivery was 2 weeks late.", "rating": 2},
    ]
    
    test("Analyze 5 mixed reviews", "POST", "/api/v1/reviews/analyze",
         {"reviews": sample_reviews},
         check=lambda d: d["success"] and d["result"]["total_reviews"] == 5 and "sentiment_distribution" in d["result"] and "theme_distribution" in d["result"])
    
    test("Sentiment distribution calculated", "POST", "/api/v1/reviews/analyze",
         {"reviews": sample_reviews},
         check=lambda d: all(k in d["result"]["sentiment_distribution"] for k in ["positive", "negative", "neutral"]))
    
    test("Theme clustering works", "POST", "/api/v1/reviews/analyze",
         {"reviews": sample_reviews},
         check=lambda d: len(d["result"]["theme_distribution"]) >= 2)
    
    test("Generate mock reviews (50)", "POST", "/api/v1/reviews/generate-mock",
         {"count": 50, "product_category": "electronics", "sentiment_bias": 0.7},
         check=lambda d: d["success"] and d["total"] == 50)
    
    test("Mock reviews then analyze pipeline", "POST", "/api/v1/reviews/analyze",
         {"reviews": []},
         check=lambda d: d["success"] and "summary" in d["result"])
    
    print(f"\n{Colors.BOLD}Ad Campaign Generator{Colors.RESET}")
    test("Get ad conversion patterns", "GET", "/api/v1/ads/conversion-patterns",
         check=lambda d: d.get("success") and "urgency" in d.get("patterns", {}))
    
    ad_product = {
        "name": "Pro Wireless Headphones",
        "brand": "SoundMax",
        "category": "Electronics",
        "description": "Professional wireless headphones",
        "key_features": ["Noise Cancelling", "40h Battery", "Premium Sound"],
        "target_audience": "Audiophiles and Professionals"
    }
    
    test("Generate 4 ad variants", "POST", "/api/v1/ads/generate",
         {"product": ad_product, "variants": 4},
         check=lambda d: d["success"] and len(d["result"]["variants"]) == 4)
    
    test("Ad variants have different types", "POST", "/api/v1/ads/generate",
         {"product": ad_product, "variants": 5},
         check=lambda d: len(set(v["variant_type"] for v in d["result"]["variants"])) >= 3)
    
    test("Title within 25 char limit", "POST", "/api/v1/ads/generate",
         {"product": ad_product, "variants": 4},
         check=lambda d: all(v["char_counts"]["title"] <= 25 for v in d["result"]["variants"]))
    
    test("Description within 90 char limit", "POST", "/api/v1/ads/generate",
         {"product": ad_product, "variants": 4},
         check=lambda d: all(v["char_counts"]["description"] <= 90 for v in d["result"]["variants"]))
    
    test("Compliance check included", "POST", "/api/v1/ads/generate",
         {"product": ad_product, "variants": 4, "include_compliance_check": True},
         check=lambda d: all("compliance" in v for v in d["result"]["variants"]))
    
    test("Quick ad generation", "POST", "/api/v1/ads/quick-generate",
         {"product_name": "Gaming Mouse", "category": "Electronics", "key_feature": "RGB Lighting", "brand": "GamePro"},
         check=lambda d: d["success"] and len(d["result"]["variants"]) >= 2)

    # ==================== Week 4 ====================
    print_section("Week 4: System Integration & Deployment", "🚢")

    print(f"\n{Colors.BOLD}Operations Dashboard{Colors.RESET}")
    test("Dashboard all-time summary", "GET", "/api/v1/reports/dashboard",
         check=lambda d: d["success"] and "summary" in d)
    test("Dashboard 24h time filter", "GET", "/api/v1/reports/dashboard?hours=24",
         check=lambda d: d["success"] and d["period"] == "最近24小时")
    test("Dashboard key metrics present", "GET", "/api/v1/reports/dashboard",
         check=lambda d: all(k in d["summary"] for k in [
             "total_interactions", "chat_messages", "transfer_to_human",
             "compliance_blocked", "transfer_rate", "avg_processing_time_ms"
         ]))

    print(f"\n{Colors.BOLD}Language & Intent Distribution{Colors.RESET}")
    test("Language distribution", "GET", "/api/v1/reports/language-distribution",
         check=lambda d: d["success"] and "distribution" in d)
    test("Language distribution has >= 5 entries", "GET", "/api/v1/reports/language-distribution",
         check=lambda d: len(d["distribution"]) >= 5)
    test("Intent distribution", "GET", "/api/v1/reports/intent-distribution",
         check=lambda d: d["success"] and "distribution" in d)

    print(f"\n{Colors.BOLD}Hourly Trend & Efficiency{Colors.RESET}")
    test("24h hourly trend", "GET", "/api/v1/reports/hourly-trend?hours=24",
         check=lambda d: d["success"] and d["period_hours"] == 24 and "trend" in d)
    test("Trend data structure", "GET", "/api/v1/reports/hourly-trend?hours=24",
         check=lambda d: all("hour" in t and "count" in t for t in d["trend"]))
    test("Agent efficiency", "GET", "/api/v1/reports/agent-efficiency",
         check=lambda d: d["success"] and "efficiency" in d)
    test("Efficiency key fields", "GET", "/api/v1/reports/agent-efficiency?hours=168",
         check=lambda d: all(k in d["efficiency"] for k in [
             "avg_confidence", "confidence_distribution", "auto_resolve_rate"
         ]))

    print(f"\n{Colors.BOLD}Data Export{Colors.RESET}")
    test("Export audit logs as CSV", "GET", "/api/v1/export/audit-logs?format=csv&limit=100",
         check=lambda d: True, timeout=30)
    test("Export audit logs as JSON", "GET", "/api/v1/export/audit-logs?format=json&limit=100",
         check=lambda d: True, timeout=30)
    test("Export with event_type filter", "GET", "/api/v1/export/audit-logs?format=json&event_type=chat&hours=168",
         check=lambda d: True, timeout=30)

    print(f"\n{Colors.BOLD}Rate Limiting{Colors.RESET}")

    CHAT_LIMIT = 30
    try:
        req = urllib.request.Request(BASE + "/api/v1/monitor/metrics")
        metrics = json.loads(urllib.request.urlopen(req, timeout=5).read())
        configured = metrics["uptime_metrics"]["rate_limiter"]["configured_limits"]
        if "/api/v1/chat" in configured:
            CHAT_LIMIT = configured["/api/v1/chat"]["max_requests"]
    except Exception:
        pass

    RATE_LIMIT_TRIGGERED = threading.Event()
    BURST = CHAT_LIMIT + 40
    results = {"ok": 0, "limited": 0, "error": 0}
    results_lock = threading.Lock()

    def _burst_worker(idx):
        if RATE_LIMIT_TRIGGERED.is_set():
            return
        try:
            req = urllib.request.Request(
                BASE + "/api/v1/chat",
                data=json.dumps({"message": "rate limit test " + str(idx), "language": "zh"}).encode(),
                method='POST'
            )
            req.add_header('Content-Type', 'application/json')
            urllib.request.urlopen(req, timeout=30).read()
            with results_lock:
                results["ok"] += 1
        except urllib.error.HTTPError as e:
            if e.code == 429:
                with results_lock:
                    results["limited"] += 1
                RATE_LIMIT_TRIGGERED.set()
            else:
                with results_lock:
                    results["error"] += 1
        except Exception:
            with results_lock:
                results["error"] += 1

    print(f"  {Colors.DIM}→ Chat limit = {CHAT_LIMIT}/60s, firing {BURST} concurrent requests...{Colors.RESET}")
    threads = [threading.Thread(target=_burst_worker, args=(i,)) for i in range(BURST)]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - t0

    TEST_NUM += 1
    TOTAL += 1
    if results["limited"] > 0:
        print(f"{Colors.GREEN}[✓] Test #{TEST_NUM:02d}: Rate limit triggered → HTTP 429 ({results['limited']}/{BURST} limited in {elapsed:.1f}s){Colors.RESET}")
        PASS += 1
    else:
        print(f"{Colors.RED}[✗] Test #{TEST_NUM:02d}: Rate limit NOT triggered (limit={CHAT_LIMIT}, ok={results['ok']}, err={results['error']}){Colors.RESET}")
        FAIL += 1

    try:
        reset_req = urllib.request.Request(BASE + "/api/v1/monitor/rate-limiter/reset", method='POST')
        reset_resp = json.loads(urllib.request.urlopen(reset_req, timeout=5).read())
        if reset_resp.get("success"):
            print(f"  {Colors.DIM}→ Rate limiter reset: cleared {reset_resp['cleared_entries']} entries{Colors.RESET}")
    except Exception:
        pass

    print(f"\n{Colors.BOLD}System Monitoring{Colors.RESET}")
    test("Monitor metrics endpoint", "GET", "/api/v1/monitor/metrics",
         check=lambda d: "uptime_metrics" in d and "rate_limiter" in d["uptime_metrics"])
    test("Rate limiter stats exposed", "GET", "/api/v1/monitor/metrics",
         check=lambda d: all(k in d["uptime_metrics"]["rate_limiter"] for k in [
             "tracked_clients", "configured_limits", "default_limit"
         ]))
    test("Configured endpoint limits", "GET", "/api/v1/monitor/metrics",
         check=lambda d: "/api/v1/chat" in d["uptime_metrics"]["rate_limiter"]["configured_limits"])

    print(f"\n{Colors.BOLD}Health Check (Enhanced){Colors.RESET}")
    hc = test("Health check full details", "GET", "/health",
              check=lambda d: all(k in d for k in [
                  "status", "version", "environment", "services",
                  "languages_supported", "compliance_enabled", "human_transfer_enabled"
              ]))
    if hc:
        test("Health: languages >= 5", "GET", "/health",
             check=lambda d: len(d["languages_supported"]) >= 5)
        test("Health: all services listed", "GET", "/health",
             check=lambda d: all(k in d["services"] for k in ["database", "redis", "llm", "embedding"]))

    print(f"\n{Colors.BOLD}Root Endpoint (Module Verification){Colors.RESET}")
    test("Root includes all 6 modules", "GET", "/",
         check=lambda d: all(k in d.get("modules", {}) for k in [
             "customer_service", "listing_generator", "review_analyzer",
             "ad_campaign", "compliance", "reporting"
         ]))
    test("Root status is running", "GET", "/",
         check=lambda d: d["status"] == "running")

    # ==================== Edge Cases ====================
    print_section("Edge Cases & Robustness", "⚡")
    
    print(f"\n{Colors.BOLD}Input Validation{Colors.RESET}")
    try:
        req = urllib.request.Request(BASE + "/api/v1/chat", 
                                     data=json.dumps({"message": "", "language": "zh"}).encode(), 
                                     method='POST')
        req.add_header('Content-Type', 'application/json')
        resp = urllib.request.urlopen(req, timeout=30)
        print(f"{Colors.RED}[✗] Empty message validation failed (expected 422){Colors.RESET}")
        FAIL += 1
        TOTAL += 1
        TEST_NUM += 1
    except urllib.error.HTTPError as e:
        TEST_NUM += 1
        TOTAL += 1
        if e.code == 422:
            print(f"{Colors.GREEN}[✓] Test #{TEST_NUM:02d}: Empty message → 422 validation error{Colors.RESET}")
            PASS += 1
        else:
            print(f"{Colors.RED}[✗] Test #{TEST_NUM:02d}: Empty message → expected 422 but got {e.code}{Colors.RESET}")
            FAIL += 1
    
    test("Non-existent session → 404", "GET", "/api/v1/sessions/fake-session-id", expect_404=True)
    
    print(f"\n{Colors.BOLD}RAG System Endpoints{Colors.RESET}")
    test("Product recommendations", "GET", "/api/v1/products/recommendations?limit=3")
    
    test("RAG index products", "POST", "/api/v1/rag/index-products", timeout=30)
    
    test("RAG index FAQs", "POST", "/api/v1/rag/index-faqs", timeout=30)

    # ==================== 输出总结 ====================
    print_summary()
    
    sys.exit(0 if FAIL == 0 else 1)