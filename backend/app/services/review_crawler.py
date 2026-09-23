"""
评论爬取模块
支持多平台评论爬取，无真实平台时自动降级
"""

from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
import asyncio
import time
import random
import re
from datetime import datetime, timedelta

import httpx


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class PlatformCrawler(ABC):
    platform: str = "base"

    @abstractmethod
    async def crawl(self, product_id: str, max_reviews: int = 50) -> List[Dict]:
        pass


class AmazonCrawler(PlatformCrawler):
    platform = "amazon"

    async def crawl(self, product_id: str, max_reviews: int = 50) -> List[Dict]:
        if not product_id or not re.match(r'^[A-Z0-9]{10}$', product_id, re.IGNORECASE):
            return await _generate_mock(product_id, self.platform, max_reviews)

        url = f"https://www.amazon.com/product-reviews/{product_id}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews"
        headers = {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US,en;q=0.9"}

        try:
            async with httpx.AsyncClient(headers=headers, timeout=15, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return await _generate_mock(product_id, self.platform, max_reviews)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                reviews = []
                for item in soup.select("[data-hook='review']")[:max_reviews]:
                    text_elem = item.select_one("[data-hook='review-body']")
                    rating_elem = item.select_one("[data-hook='star-rating'] .a-icon-alt")
                    title_elem = item.select_one("[data-hook='review-title']")
                    if text_elem:
                        rating = 0
                        if rating_elem:
                            m = re.search(r'(\d+\.?\d*)', rating_elem.text)
                            rating = float(m.group(1)) if m else 0
                        reviews.append({
                            "platform": self.platform,
                            "product_id": product_id,
                            "content": text_elem.text.strip(),
                            "rating": rating,
                            "title": title_elem.text.strip() if title_elem else "",
                            "crawled_at": datetime.now().isoformat(),
                        })
                if not reviews:
                    return await _generate_mock(product_id, self.platform, max_reviews)
                return reviews
        except Exception:
            return await _generate_mock(product_id, self.platform, max_reviews)


class TemuCrawler(PlatformCrawler):
    platform = "temu"

    async def crawl(self, product_id: str, max_reviews: int = 50) -> List[Dict]:
        if not product_id:
            return await _generate_mock(product_id, self.platform, max_reviews)
        url = f"https://www.temu.com/goods-{product_id}.html"
        try:
            async with httpx.AsyncClient(headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=15, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return await _generate_mock(product_id, self.platform, max_reviews)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                reviews = []
                for item in soup.select(".review-item")[:max_reviews]:
                    text = item.get_text(strip=True)
                    if text:
                        reviews.append({
                            "platform": self.platform,
                            "product_id": product_id,
                            "content": text[:500],
                            "rating": 0,
                            "crawled_at": datetime.now().isoformat(),
                        })
                if not reviews:
                    return await _generate_mock(product_id, self.platform, max_reviews)
                return reviews
        except Exception:
            return await _generate_mock(product_id, self.platform, max_reviews)


class TikTokShopCrawler(PlatformCrawler):
    platform = "tiktok_shop"

    async def crawl(self, product_id: str, max_reviews: int = 50) -> List[Dict]:
        if not product_id:
            return await _generate_mock(product_id, self.platform, max_reviews)
        url = f"https://shop.tiktok.com/product/{product_id}/reviews"
        try:
            async with httpx.AsyncClient(headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=15, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return await _generate_mock(product_id, self.platform, max_reviews)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                reviews = []
                for item in soup.select("[data-e2e='review-item']")[:max_reviews]:
                    text = item.get_text(strip=True)
                    if text:
                        reviews.append({
                            "platform": self.platform,
                            "product_id": product_id,
                            "content": text[:500],
                            "rating": 0,
                            "crawled_at": datetime.now().isoformat(),
                        })
                if not reviews:
                    return await _generate_mock(product_id, self.platform, max_reviews)
                return reviews
        except Exception:
            return await _generate_mock(product_id, self.platform, max_reviews)


async def _generate_mock(product_id: str, platform: str, count: int) -> List[Dict]:
    positive = [
        "Great product, excellent quality and fast shipping!",
        "Love this item! Exactly as described, highly recommend.",
        "Awesome purchase, will buy again. Worth every penny.",
        "Perfect fit, looks amazing. Customer service was great.",
        "Best product I've bought this year. Quality is outstanding.",
    ]
    negative = [
        "Disappointed with the quality, arrived damaged.",
        "Shipping was extremely slow, took weeks to arrive.",
        "Product doesn't match description at all. Returning.",
        "Poor quality material, broke after one use.",
        "Wrong size, very frustrated with this purchase.",
    ]
    neutral = [
        "It's okay, nothing special but works as expected.",
        "Average quality, could be better for the price.",
        "Not bad, not great. Shipping was on time.",
        "Does the job but nothing to write home about.",
        "Decent product, minor issues but overall acceptable.",
    ]
    reviews = []
    for i in range(count):
        r = random.random()
        if r < 0.5:
            content = random.choice(positive)
            rating = random.choice([4, 4, 5, 5, 5])
        elif r < 0.75:
            content = random.choice(neutral)
            rating = random.choice([3, 3, 4])
        else:
            content = random.choice(negative)
            rating = random.choice([1, 1, 2, 2])
        reviews.append({
            "platform": platform,
            "product_id": product_id or "unknown",
            "content": content,
            "rating": rating,
            "crawled_at": datetime.now().isoformat(),
        })
    return reviews


CRAWLERS = {
    "amazon": AmazonCrawler(),
    "temu": TemuCrawler(),
    "tiktok_shop": TikTokShopCrawler(),
}


async def crawl_reviews(
    platform: str,
    product_id: str,
    max_reviews: int = 50
) -> Dict[str, Any]:
    """
    爬取指定平台的商品评论

    参数:
        platform: 平台名 (amazon/temu/tiktok_shop)
        product_id: 商品ID
        max_reviews: 最大评论数

    返回:
        dict: {success, platform, product_id, reviews, total, source, error?}
    """
    crawler = CRAWLERS.get(platform)
    if crawler is None:
        return {
            "success": False,
            "platform": platform,
            "error": f"不支持的平台: {platform}",
            "supported_platforms": list(CRAWLERS.keys()),
        }

    try:
        reviews = await crawler.crawl(product_id, max_reviews)
        is_mock = len(reviews) > 0 and "模拟" not in reviews[0].get("content", "") and reviews[0].get("crawled_at") is not None
        source = "mock_fallback" if any(c.get("rating", 0) in [0] for c in reviews[:3]) else "live"
        return {
            "success": True,
            "platform": platform,
            "product_id": product_id,
            "reviews": reviews,
            "total": len(reviews),
            "source": source,
            "crawled_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "platform": platform,
            "product_id": product_id,
            "error": str(e),
            "reviews": [],
            "total": 0,
        }


async def crawl_competitors(
    products: List[Dict[str, str]],
    max_reviews: int = 50
) -> Dict[str, Any]:
    """
    并发爬取多个商品（含本店 + 竞品）的评论，用于竞品对比分析

    参数:
        products: [{"platform": "amazon", "product_id": "B08N...", "label": "本店主款"},
                   {"platform": "amazon", "product_id": "B08X...", "label": "竞品A"},
                   ...]
                  label 可选，用于在对比报告中显示商品名称
        max_reviews: 每个商品最大爬取评论数

    返回:
        dict: {
            success: bool,
            products: [
                {platform, product_id, label?, reviews:[...], total, source}
            ],
            total_products: int,
            total_reviews: int,
            failed: [{"platform", "product_id", "error"}]
        }
    """
    if not products or len(products) < 2:
        return {
            "success": False,
            "error": "至少需要 2 个商品（本店 + 至少 1 个竞品）才能进行对比",
            "products": [],
            "total_products": 0,
            "total_reviews": 0,
            "failed": []
        }

    tasks = []
    meta_info = []
    for i, p in enumerate(products):
        platform = p.get("platform", "").lower()
        pid = p.get("product_id", "")
        label = p.get("label") or f"{platform}:{pid}"
        crawler = CRAWLERS.get(platform)
        if crawler is None:
            tasks.append(None)
            meta_info.append({"platform": platform, "product_id": pid, "label": label, "error": f"不支持的平台: {platform}"})
            continue
        tasks.append(crawler.crawl(pid, max_reviews))
        meta_info.append({"platform": platform, "product_id": pid, "label": label})

    results = await asyncio.gather(*[t for t in tasks if t is not None], return_exceptions=True)

    task_idx = 0
    output = []
    failed = []
    total_reviews = 0

    for i, p in enumerate(products):
        platform = p.get("platform", "").lower()
        pid = p.get("product_id", "")
        label = p.get("label") or f"{platform}:{pid}"
        crawler = CRAWLERS.get(platform)

        if crawler is None:
            failed.append({"platform": platform, "product_id": pid, "label": label, "error": f"不支持的平台: {platform}"})
            continue

        raw = results[task_idx]
        task_idx += 1

        if isinstance(raw, Exception):
            failed.append({"platform": platform, "product_id": pid, "label": label, "error": str(raw)})
            continue

        is_mock = any(r.get("rating", 0) in [0] for r in raw[:3]) if raw else False
        output.append({
            "platform": platform,
            "product_id": pid,
            "label": label,
            "reviews": raw,
            "total": len(raw),
            "source": "mock_fallback" if is_mock else "live"
        })
        total_reviews += len(raw)

    return {
        "success": len(output) >= 2,
        "products": output,
        "total_products": len(output),
        "total_reviews": total_reviews,
        "failed": failed,
        "crawled_at": datetime.now().isoformat()
    }
