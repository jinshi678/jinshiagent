"""日志配置 — 基于 Rich 的统一日志体系

提供美观的控制台输出和可选的文件日志。
基于 Python 标准 logging 模块，使用 Rich Handler 美化输出。

使用示例::

    from jinshiagent.utils.logging import setup_logging

    setup_logging(level="DEBUG", log_file="./logs/app.log")
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """初始化全局日志配置。

    Args:
        level: 日志级别 (DEBUG / INFO / WARNING / ERROR / CRITICAL)
        log_file: 日志文件路径（None 则仅输出到控制台）
        format_string: 自定义日志格式

    Returns:
        根 Logger 对象
    """
    root_logger = logging.getLogger("jinshiagent")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除已有 Handler
    root_logger.handlers.clear()

    # 控制台 Handler — 优先使用 Rich
    try:
        from rich.logging import RichHandler

        console_handler = RichHandler(
            rich_tracebacks=True,
            show_path=False,
            markup=True,
        )
    except ImportError:
        console_handler = logging.StreamHandler(sys.stdout)

    fmt = format_string or "%(message)s"
    console_handler.setFormatter(logging.Formatter(fmt))
    root_logger.addHandler(console_handler)

    # 文件 Handler（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_fmt = format_string or "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        file_handler.setFormatter(logging.Formatter(file_fmt))
        root_logger.addHandler(file_handler)

    return root_logger
