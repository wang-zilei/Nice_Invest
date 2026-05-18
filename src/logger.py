"""
logger.py — 结构化日志系统
双输出：终端 stdout + 文件 logs/server.log
记录用户行为、分析请求、Agent 状态、API 异常等。
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 确保 logs 目录存在
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "server.log"

# ============================================================
# 自定义 Formatter
# ============================================================
class NiceFormatter(logging.Formatter):
    """结构化格式：[时间] [级别] [模块] 消息"""

    grey = "\x1b[38;20m"
    green = "\x1b[32;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    COLORS = {
        logging.DEBUG: grey,
        logging.INFO: green,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red,
    }

    def format(self, record):
        # 终端格式（带颜色）
        log_fmt = f"{self.COLORS.get(record.levelno, self.grey)}[%(asctime)s] [%(levelname)-5s] [%(module)s] %(message)s{self.reset}"
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)


class FileFormatter(logging.Formatter):
    """文件格式（无颜色）"""
    def format(self, record):
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)-5s] [%(module)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return formatter.format(record)


# ============================================================
# 构建 Logger
# ============================================================
logger = logging.getLogger("nice_invest")
logger.setLevel(logging.DEBUG)
logger.handlers.clear()

# 终端 handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(NiceFormatter())
logger.addHandler(console_handler)

# 文件 handler
file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(FileFormatter())
logger.addHandler(file_handler)


# ============================================================
# 统计摘要打印
# ============================================================
def print_startup_summary():
    """启动时打印服务信息 + 统计摘要"""
    from src.auth import user_store

    total_users = user_store.total_users

    logger.info("=" * 50)
    logger.info("Nice Invest API v0.2.0 启动")
    logger.info(f"  监听地址: http://0.0.0.0:8000")
    logger.info(f"  日志文件: {LOG_FILE}")
    logger.info(f"  累计注册用户: {total_users}")
    logger.info("=" * 50)
