"""
内容生成模块
整合: Listing生成 (Amazon/Temu/TikTok Shop) + PPC广告词生成引擎
"""

import re
import json
import random
from typing import Dict, List, Optional, Any
from datetime import datetime


PLATFORM_TEMPLATES = {
    "amazon": {
        "name": "Amazon",
        "title_max_chars": 200,
        "bullet_points_count": 5,
        "bullet_max_chars": 250,
        "description_max_chars": 2000,
        "a_plus_enabled": True,
        "a_plus_sections": ["品牌故事", "产品亮点", "使用场景", "规格参数"],
        "style_guide": "Amazon风格: 标题要包含品牌+核心关键词+关键属性，五点要突出卖点和解决用户痛点"
    },
    "temu": {
        "name": "Temu",
        "title_max_chars": 80,
        "bullet_points_count": 3,
        "bullet_max_chars": 150,
        "description_max_chars": 500,
        "a_plus_enabled": False,
        "a_plus_sections": [],
        "style_guide": "Temu风格: 标题要简洁有冲击力，突出性价比和核心卖点，适合移动端快速浏览"
    },
    "tiktok_shop": {
        "name": "TikTok Shop",
        "title_max_chars": 60,
        "bullet_points_count": 4,
        "bullet_max_chars": 180,
        "description_max_chars": 800,
        "a_plus_enabled": True,
        "a_plus_sections": ["产品亮点", "使用场景"],
        "style_guide": "TikTok Shop风格: 标题要抓眼球，适合短视频流量转化，口语化但专业"
    }
}


def _generate_title(product: Dict, platform: str, variant_num: int = 1) -> str:
    templates = {
        "amazon": [
            "{brand} {name} - {key_feature} {category} for {audience}",
            "{brand} Premium {category} - {name} with {key_feature}, {key_feature2}",
            "{brand} {category} {name} | {key_feature} | {audience}"
        ],
        "temu": [
            "{name} | {key_feature} | Best {category}",
            "{brand} {name} - {key_feature} {category}",
            "🔥 {name} {key_feature} {category} Hot Sale!"
        ],
        "tiktok_shop": [
            "{name} - {key_feature} You Need!",
            "{brand} {name} | {key_feature}",
            "✨ {name} {key_feature} {category}"
        ]
    }

    tmpl_list = templates.get(platform, templates["amazon"])
    tmpl = tmpl_list[(variant_num - 1) % len(tmpl_list)]

    features = product.get("key_features", [])
    feature1 = features[0] if len(features) > 0 else product.get("description", "Premium Quality")[:30]
    feature2 = features[1] if len(features) > 1 else "Durable & Reliable"

    return tmpl.format(
        brand=product.get("brand", "Premium"),
        name=product.get("name", "Product"),
        category=product.get("category", ""),
        key_feature=feature1,
        key_feature2=feature2,
        audience=product.get("target_audience", "Everyone")
    )


def _generate_bullets(product: Dict, platform: str, variant_num: int = 1) -> List[str]:
    feat_template = {
        "amazon": "✅ {feature}",
        "temu": "⚡ {feature}",
        "tiktok_shop": "⭐ {feature}"
    }

    feat_format = feat_template.get(platform, feat_template["amazon"])
    bullet_count = PLATFORM_TEMPLATES.get(platform, PLATFORM_TEMPLATES["amazon"])["bullet_points_count"]

    features = product.get("key_features", [])
    if len(features) < bullet_count:
        default_features = [
            "High Quality Materials",
            "Easy to Use",
            "Perfect Gift Idea",
            "Fast Shipping",
            "Excellent Customer Service"
        ]
        features = features + default_features[:bullet_count - len(features)]

    start_idx = (variant_num - 1) % max(1, len(features) - bullet_count + 1)
    selected = features[start_idx:start_idx + bullet_count]

    return [feat_format.format(feature=f) for f in selected]


def _generate_description(product: Dict, platform: str, variant_num: int = 1) -> str:
    style_map = {
        "amazon": (
            "Experience the perfect blend of quality and functionality with our {brand} {name}. "
            "{description}\n\n"
            "Key Benefits:\n"
            "🎯 Designed for {audience}\n"
            "🏆 Premium craftsmanship you can feel\n"
            "💯 Satisfaction guaranteed\n\n"
            "Whether you're looking for everyday essentials or something special, our {category} "
            "delivers excellence in every detail."
        ),
        "temu": (
            "Meet your new favorite {category}! The {brand} {name} is here to make your life better. "
            "{description}\n"
            "Order now and enjoy great quality at an amazing price!"
        ),
        "tiktok_shop": (
            "You'll love our {brand} {name}! {description}\n"
            "{audience}, this one's for you! Shop now and join thousands of happy customers. 🛍️✨"
        )
    }

    template = style_map.get(platform, style_map["amazon"])

    return template.format(
        brand=product.get("brand", "Premium"),
        name=product.get("name", "Product"),
        description=product.get("description", "Made with premium materials for lasting quality"),
        category=product.get("category", "Product"),
        audience=product.get("target_audience", "everyone")
    )


def _generate_a_plus_content(product: Dict, platform: str) -> Optional[Dict]:
    if not PLATFORM_TEMPLATES.get(platform, {}).get("a_plus_enabled"):
        return None

    return {
        "brand_story": f"At {product.get('brand', 'Our Brand')}, we believe in creating exceptional "
                       f"{product.get('category', 'products')} that enrich people's lives. "
                       f"Founded on the principles of quality and innovation.",
        "product_highlights": [
            f"🎨 Beautifully designed {product.get('category', 'product')} that complements any style",
            f"🔧 Built with premium materials for long-lasting durability",
            f"💡 Thoughtful features that make everyday life easier"
        ],
        "use_cases": [
            f"Perfect for {product.get('target_audience', 'everyone')}",
            "Ideal for both professional and personal use",
            "Makes a thoughtful gift for special occasions"
        ],
        "specs": [
            f"Brand: {product.get('brand', 'Premium')}",
            f"Category: {product.get('category', 'General')}",
            f"Features: {', '.join(product.get('key_features', ['Premium Quality']))}"
        ]
    }


class ListingGenerator:
    """Listing生成服务"""

    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
        return cls._instance

    def generate(
        self,
        product: Dict,
        platform: str = "amazon",
        variants: int = 1,
        language: str = "en"
    ) -> Dict[str, Any]:
        if platform not in PLATFORM_TEMPLATES:
            raise ValueError(f"不支持的平台: {platform}，可选: {list(PLATFORM_TEMPLATES.keys())}")

        if variants < 1 or variants > 5:
            raise ValueError("变体数量必须在 1-5 之间")

        template = PLATFORM_TEMPLATES[platform]
        variant_results = []

        for i in range(1, variants + 1):
            title = _generate_title(product, platform, i)
            bullets = _generate_bullets(product, platform, i)
            description = _generate_description(product, platform, i)
            a_plus = _generate_a_plus_content(product, platform)

            variant_results.append({
                "variant": i,
                "title": title[:template["title_max_chars"]],
                "bullet_points": [b[:template["bullet_max_chars"]] for b in bullets],
                "description": description[:template["description_max_chars"]],
                "a_plus": a_plus,
                "char_counts": {
                    "title": len(title[:template["title_max_chars"]]),
                    "description": len(description[:template["description_max_chars"]]),
                    "platform_limits": {
                        "title_max": template["title_max_chars"],
                        "description_max": template["description_max_chars"]
                    }
                }
            })

        return {
            "platform": platform,
            "platform_name": template["name"],
            "style_guide": template["style_guide"],
            "variants": variant_results,
            "generated_at": datetime.now().isoformat(),
            "total_variants": variants
        }

    def batch_generate(
        self,
        products: List[Dict],
        platform: str = "amazon",
        variants_per_product: int = 1
    ) -> Dict[str, Any]:
        results = []
        for product in products:
            try:
                listing = self.generate(product, platform, variants_per_product)
                results.append({
                    "product_name": product.get("name", "Unknown"),
                    "sku": product.get("sku", ""),
                    "listings": listing,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "product_name": product.get("name", "Unknown"),
                    "sku": product.get("sku", ""),
                    "success": False,
                    "error": str(e)
                })

        return {
            "platform": platform,
            "total": len(products),
            "success_count": sum(1 for r in results if r["success"]),
            "failed_count": sum(1 for r in results if not r["success"]),
            "results": results,
            "generated_at": datetime.now().isoformat()
        }

    def get_platforms(self) -> List[Dict]:
        return [
            {
                "key": k,
                "name": v["name"],
                "title_max_chars": v["title_max_chars"],
                "bullet_points_count": v["bullet_points_count"],
                "description_max_chars": v["description_max_chars"],
                "a_plus_enabled": v["a_plus_enabled"],
                "style_guide": v["style_guide"]
            }
            for k, v in PLATFORM_TEMPLATES.items()
        ]


HIGH_CONVERSION_PATTERNS = {
    "urgency": [
        "Limited Time Offer", "Last Chance", "While Supplies Last",
        "Deal Ends Soon", "Don't Miss Out", "Hurry", "Flash Sale",
        "限时特价", "最后机会", "马上抢购", "仅剩XX件"
    ],
    "value": [
        "Best Value", "Top Quality", "Premium", "High Quality",
        "Affordable", "Economical", "Budget Friendly",
        "性价比之王", "高品质", "超值", "物美价廉"
    ],
    "social_proof": [
        "Best Seller", "Top Rated", "#1 Choice", "Customer Favorite",
        "Trending", "Popular", "Most Loved",
        "热销榜第一", "好评如潮", "爆款"
    ],
    "action": [
        "Shop Now", "Order Today", "Get Yours", "Click to Buy",
        "Add to Cart", "Grab Your Copy",
        "立即购买", "点击抢购", "加入购物车"
    ],
    "benefit": [
        "Free Shipping", "Fast Delivery", "Easy Returns", "Money Back",
        "Guaranteed", "Risk Free", "Warranty Included",
        "免运费", "快速发货", "无忧退换", "品质保证"
    ]
}

TITLE_MAX_CHARS = 25
DESCRIPTION_MAX_CHARS = 90


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "…"


def _generate_ad_title(product: Dict, variant_type: str = "urgency", variant_num: int = 1) -> str:
    templates = [
        "{pattern} {name}",
        "{name} - {pattern}",
        "{pattern}: {name}",
        "{brand} {name} | {pattern}",
        "{pattern} {brand} {name}"
    ]

    tmpl = templates[(variant_num - 1) % len(templates)]
    pattern_words = HIGH_CONVERSION_PATTERNS.get(variant_type, HIGH_CONVERSION_PATTERNS["value"])
    pattern = pattern_words[(variant_num - 1) % len(pattern_words)]

    title = tmpl.format(
        pattern=pattern,
        name=product.get("name", "Product")[:15],
        brand=product.get("brand", "")[:10]
    )
    return _truncate(title, TITLE_MAX_CHARS)


def _generate_ad_description(product: Dict, variant_type: str = "urgency", variant_num: int = 1) -> str:
    feat = product.get("key_features", [product.get("description", "High Quality")])
    if isinstance(feat, list):
        feat = feat[0]

    call_to_actions = HIGH_CONVERSION_PATTERNS.get("action", [])
    benefits = HIGH_CONVERSION_PATTERNS.get("benefit", [])

    cta = call_to_actions[(variant_num - 1) % len(call_to_actions)]
    benefit = benefits[(variant_num - 1) % len(benefits)]

    templates = [
        "{feature}. {benefit}. {cta}!",
        "{brand} {name} - {feature}. {benefit}. {cta}!",
        "Experience {feature}. {benefit} included. {cta}!",
        "{feature}. {benefit} guarantee. {cta} today!",
        "Premium {category}. {feature}. {cta} - {benefit}!"
    ]

    tmpl = templates[(variant_num - 1) % len(templates)]
    desc = tmpl.format(
        feature=feat[:40],
        benefit=benefit,
        cta=cta,
        brand=product.get("brand", ""),
        name=product.get("name", "Product"),
        category=product.get("category", "Product")
    )
    return _truncate(desc, DESCRIPTION_MAX_CHARS)


def _check_ad_compliance(title: str, description: str) -> Dict[str, Any]:
    issues = []

    superlatives = ["best", "worst", "#1", "top", "only", "exclusive", "guaranteed", "100%", "永久", "绝对", "唯一"]
    text = (title + " " + description).lower()

    for superlative in superlatives:
        if superlative in text:
            issues.append({
                "issue": "superlative_claim",
                "text": superlative,
                "severity": "medium",
                "suggestion": f"移除或替换绝对化用词 '{superlative}'"
            })

    restricted_words = ["free", "guarantee", "money back", "无需", "全额退款"]
    for word in restricted_words:
        if word in text:
            issues.append({
                "issue": "restricted_term",
                "text": word,
                "severity": "low",
                "suggestion": f"确认'{word}'是否满足平台使用条件"
            })

    return {
        "compliant": len(issues) == 0,
        "issues": issues,
        "total_issues": len(issues)
    }


class AdCampaignGenerator:
    """广告词生成引擎服务"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def generate(
        self,
        product: Dict,
        variants: int = 4,
        include_compliance_check: bool = True
    ) -> Dict[str, Any]:
        if variants < 2 or variants > 6:
            raise ValueError("变体数量必须在 2-6 之间")

        variant_types = list(HIGH_CONVERSION_PATTERNS.keys())
        results = []

        for i in range(1, variants + 1):
            variant_type = variant_types[(i - 1) % len(variant_types)]

            title = _generate_ad_title(product, variant_type, i)
            description = _generate_ad_description(product, variant_type, i)

            compliance = None
            if include_compliance_check:
                compliance = _check_ad_compliance(title, description)

            results.append({
                "variant": i,
                "variant_type": variant_type,
                "title": title,
                "description": description,
                "char_counts": {
                    "title": len(title),
                    "description": len(description),
                    "within_limit": len(title) <= TITLE_MAX_CHARS and len(description) <= DESCRIPTION_MAX_CHARS
                },
                "compliance": compliance
            })

        return {
            "product": {
                "name": product.get("name"),
                "brand": product.get("brand", ""),
                "category": product.get("category", "")
            },
            "platform_limits": {
                "title_max_chars": TITLE_MAX_CHARS,
                "description_max_chars": DESCRIPTION_MAX_CHARS,
                "platforms": ["Amazon PPC", "TikTok Ads", "Google Ads"]
            },
            "variants": results,
            "total_variants": variants,
            "all_compliant": all(
                v["compliance"]["compliant"] for v in results if v["compliance"]
            ) if include_compliance_check else None,
            "generated_at": datetime.now().isoformat()
        }

    def batch_generate(
        self,
        products: List[Dict],
        variants_per_product: int = 4
    ) -> Dict[str, Any]:
        results = []
        for product in products:
            try:
                ads = self.generate(product, variants_per_product)
                results.append({
                    "product_name": product.get("name", "Unknown"),
                    "success": True,
                    "ads": ads
                })
            except Exception as e:
                results.append({
                    "product_name": product.get("name", "Unknown"),
                    "success": False,
                    "error": str(e)
                })

        return {
            "total": len(products),
            "success_count": sum(1 for r in results if r["success"]),
            "results": results,
            "generated_at": datetime.now().isoformat()
        }

    def get_conversion_patterns(self) -> Dict[str, List[str]]:
        return HIGH_CONVERSION_PATTERNS

    def quick_generate(
        self,
        product_name: str,
        category: str = "",
        key_feature: str = "",
        brand: str = ""
    ) -> Dict[str, Any]:
        product = {
            "name": product_name,
            "brand": brand,
            "category": category,
            "key_features": [key_feature] if key_feature else [],
            "description": key_feature
        }
        return self.generate(product, variants=4, include_compliance_check=True)