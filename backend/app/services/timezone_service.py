"""
时区智能回复策略服务

功能：根据买家语言推断其所在时区，结合当前时间生成智能回复承诺时效
设计：不依赖外部 IP 地理位置 API，纯本地计算，零延迟
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


LANGUAGE_TIMEZONE_MAP = {
    "zh": {
        "timezone": "Asia/Shanghai",
        "label": "北京时间",
        "utc_offset": 8,
    },
    "en": {
        "timezone": "America/Los_Angeles",
        "label": "美国太平洋时间",
        "utc_offset": -8,
    },
    "es": {
        "timezone": "Europe/Madrid",
        "label": "西班牙时间",
        "utc_offset": 1,
    },
    "fr": {
        "timezone": "Europe/Paris",
        "label": "法国时间",
        "utc_offset": 1,
    },
    "de": {
        "timezone": "Europe/Berlin",
        "label": "德国时间",
        "utc_offset": 1,
    },
}


WORK_START_HOUR = 9
WORK_END_HOUR = 21
MAX_REPLY_HOURS_DURING_WORK = 2


class TimezoneService:
    """
    时区智能回复策略

    根据买家语言推断其时区，判断对方当前是否在工作时间，
    生成贴合对方时间感知的回复承诺时效文案
    """

    @staticmethod
    def get_buyer_timezone(language: str) -> dict:
        """
        根据语言推断买家时区信息

        返回：
            dict: {timezone, label, utc_offset}
        """
        return LANGUAGE_TIMEZONE_MAP.get(
            language, LANGUAGE_TIMEZONE_MAP["zh"]
        )

    @staticmethod
    def get_buyer_local_time(language: str) -> datetime:
        """获取买家所在时区的当前本地时间"""
        tz_info = TimezoneService.get_buyer_timezone(language)
        tz_name = tz_info["timezone"]
        try:
            tz = ZoneInfo(tz_name)
            return datetime.now(tz)
        except Exception:
            offset = tz_info["utc_offset"]
            return datetime.utcnow() + timedelta(hours=offset)

    @staticmethod
    def is_buyer_in_work_hours(language: str) -> bool:
        """判断买家当前是否处于工作时间（9:00-21:00）"""
        local_time = TimezoneService.get_buyer_local_time(language)
        hour = local_time.hour
        return WORK_START_HOUR <= hour < WORK_END_HOUR

    @staticmethod
    def hours_until_work_end(language: str) -> int:
        """距离买家当地工作时间结束还有多少小时（负数表示已下班）"""
        local_time = TimezoneService.get_buyer_local_time(language)
        return WORK_END_HOUR - local_time.hour

    @staticmethod
    def hours_until_work_start(language: str) -> int:
        """距离买家当地下次工作时间开始还有多少小时（正数表示待上班）"""
        local_time = TimezoneService.get_buyer_local_time(language)
        hour = local_time.hour
        if hour < WORK_START_HOUR:
            return WORK_START_HOUR - hour
        return 24 - hour + WORK_START_HOUR

    @staticmethod
    def get_reply_promise(language: str) -> dict:
        """
        生成面向买家的回复承诺时效信息

        返回：
            dict: {
                in_work_hours: bool,
                promise_text: str,       # 中文承诺文案（嵌入客服回复末尾）
                promise_localized: str,   # 多语言承诺文案
                buyer_local_time: str,    # 买家当地时间 HH:MM
            }
        """
        local_time = TimezoneService.get_buyer_local_time(language)
        is_working = TimezoneService.is_buyer_in_work_hours(language)
        hours_to_end = TimezoneService.hours_until_work_end(language)
        hours_to_start = TimezoneService.hours_until_work_start(language)
        timezone_info = TimezoneService.get_buyer_timezone(language)

        buyer_time_str = local_time.strftime("%H:%M")

        zh_working = f"（当前 {timezone_info['label']} {buyer_time_str}，工作时间内，通常 {MAX_REPLY_HOURS_DURING_WORK} 小时内回复）"
        zh_about_end = f"（当前 {timezone_info['label']} {buyer_time_str}，还剩 {hours_to_end} 小时下班，建议尽快处理）"
        zh_off_hours = f"（当前 {timezone_info['label']} {buyer_time_str}，不在工作时间内，将在约 {hours_to_start} 小时后上班第一时间回复）"

        en_working = f"(Current {timezone_info['label']} {buyer_time_str}, within work hours, usually reply within {MAX_REPLY_HOURS_DURING_WORK} hours)"
        en_about_end = f"(Current {timezone_info['label']} {buyer_time_str}, {hours_to_end} hours left before end of work)"
        en_off_hours = f"(Current {timezone_info['label']} {buyer_time_str}, outside work hours, will reply in approximately {hours_to_start} hours when we're back online)"

        es_working = f"(Hora actual en {timezone_info['label']} {buyer_time_str}, dentro del horario laboral, respuesta habitual en {MAX_REPLY_HOURS_DURING_WORK} horas)"
        es_off_hours = f"(Hora actual en {timezone_info['label']} {buyer_time_str}, fuera del horario laboral, responderemos en aproximadamente {hours_to_start} horas)"

        fr_working = f"(Heure actuelle {timezone_info['label']} {buyer_time_str}, pendant les heures ouvrées, réponse généralement sous {MAX_REPLY_HOURS_DURING_WORK} heures)"
        fr_off_hours = f"(Heure actuelle {timezone_info['label']} {buyer_time_str}, hors heures ouvrées, nous répondrons dans environ {hours_to_start} heures)"

        de_working = f"(Aktuelle {timezone_info['label']} {buyer_time_str}, während der Arbeitszeit, Antwort meist innerhalb {MAX_REPLY_HOURS_DURING_WORK} Stunden)"
        de_off_hours = f"(Aktuelle {timezone_info['label']} {buyer_time_str}, außerhalb der Arbeitszeit, wir antworten in ca. {hours_to_start} Stunden)"

        if is_working:
            if hours_to_end <= 1:
                promise_zh = zh_about_end
            else:
                promise_zh = zh_working
            promise_en = en_working
            promise_es = es_working
            promise_fr = fr_working
            promise_de = de_working
        else:
            promise_zh = zh_off_hours
            promise_en = en_off_hours
            promise_es = es_off_hours
            promise_fr = fr_off_hours
            promise_de = de_off_hours

        localized = {
            "zh": promise_zh,
            "en": promise_en,
            "es": promise_es,
            "fr": promise_fr,
            "de": promise_de,
        }

        return {
            "in_work_hours": is_working,
            "hours_to_end": hours_to_end,
            "hours_to_start": hours_to_start,
            "promise_text": promise_zh,
            "promise_localized": localized.get(language, localized["zh"]),
            "buyer_local_time": buyer_time_str,
            "timezone_label": timezone_info["label"],
        }

    @staticmethod
    def append_timezone_promise(reply_text: str, language: str) -> str:
        """
        在客服回复末尾追加时区智能承诺时效文案

        用法：在 agent.py 最终返回 response 之前调用此方法
        """
        promise = TimezoneService.get_reply_promise(language)
        return f"{reply_text}\n\n{promise['promise_localized']}"