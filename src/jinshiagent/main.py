"""JinshiAgent 项目入口

用法:
    python -m jinshiagent          # 启动交互式 Agent
    python -m jinshiagent --help   # 查看帮助
"""

import argparse
import sys

from jinshiagent.config.loader import load_config
from jinshiagent.utils.logging import setup_logging
from jinshiagent.utils.exceptions import JinshiAgentError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="jinshiagent",
        description="JinshiAgent — AI Agent 工具框架",
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细日志输出",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # 加载配置
    config = load_config(args.config)

    # 初始化日志
    log_level = "DEBUG" if args.verbose else config.get("log_level", "INFO")
    setup_logging(level=log_level, log_file=config.get("log_file"))

    # TODO: 启动 Agent REPL
    print("JinshiAgent v0.1.0 — 输入 'quit' 退出")
    print("Agent REPL 尚未实现，敬请期待。")


if __name__ == "__main__":
    try:
        main()
    except JinshiAgentError as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n再见！")
        sys.exit(0)
