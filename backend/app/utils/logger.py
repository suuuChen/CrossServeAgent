"""
日志配置
支持控制台+文件双输出，按日期滚动，结构化JSON日志
"""
import logging
import logging.handlers
import os
import json
from datetime import datetime


def setup_logging(log_dir: str = "logs", level: str = "INFO", app_name: str = "multilingual_agent"):
    os.makedirs(log_dir, exist_ok=True)

    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    json_formatter = logging.Formatter(
        fmt=json.dumps({
            "timestamp": "%(asctime)s",
            "level": "%(levelname)s",
            "logger": "%(name)s",
            "message": "%(message)s",
            "module": "%(module)s",
            "function": "%(funcName)s",
            "line": "%(lineno)d"
        })
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)

        app_file = logging.handlers.TimedRotatingFileHandler(
            filename=os.path.join(log_dir, f"{app_name}.log"),
            when="midnight",
            backupCount=30,
            encoding="utf-8"
        )
        app_file.setFormatter(formatter)
        app_file.setLevel(log_level)
        root_logger.addHandler(app_file)

        error_file = logging.handlers.TimedRotatingFileHandler(
            filename=os.path.join(log_dir, f"{app_name}_error.log"),
            when="midnight",
            backupCount=30,
            encoding="utf-8"
        )
        error_file.setLevel(logging.ERROR)
        error_file.setFormatter(formatter)
        root_logger.addHandler(error_file)

        json_file = logging.handlers.TimedRotatingFileHandler(
            filename=os.path.join(log_dir, f"{app_name}_audit.json"),
            when="midnight",
            backupCount=30,
            encoding="utf-8"
        )
        json_file.setLevel(log_level)
        json_file.setFormatter(json_formatter)
        root_logger.addHandler(json_file)

    for name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
        lg.setLevel(log_level)

    return logging.getLogger(app_name)


def get_logger(name: str = "multilingual_agent"):
    return logging.getLogger(name)