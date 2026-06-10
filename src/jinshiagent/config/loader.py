"""配置加载器 — 从 YAML 文件、环境变量和 .env 文件加载配置

优先级（从高到低）：
1. 环境变量
2. .env 文件
3. YAML 配置文件
4. 默认值

使用示例::

    from jinshiagent.config import load_config

    config = load_config("config.yaml")
    print(config["openai_model"])
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from jinshiagent.utils.exceptions import ConfigError


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    """加载配置文件。

    从指定路径读取 YAML 配置，并合并 .env 文件和环境变量。

    Args:
        config_path: YAML 配置文件路径

    Returns:
        合并后的配置字典

    Raises:
        ConfigError: 配置文件格式错误或路径不存在时
    """
    config: dict[str, Any] = {}

    # 1. 加载 .env 文件
    _load_dotenv()

    # 2. 加载 YAML 配置
    yaml_config = _load_yaml(config_path)
    if yaml_config:
        config.update(yaml_config)

    # 3. 环境变量覆盖
    env_mapping = {
        "OPENAI_API_KEY": "openai_api_key",
        "OPENAI_API_BASE": "openai_api_base",
        "OPENAI_MODEL": "openai_model",
        "AGENT_MAX_ITERATIONS": "agent_max_iterations",
        "AGENT_VERBOSE": "agent_verbose",
        "LOG_LEVEL": "log_level",
        "LOG_FILE": "log_file",
    }
    for env_key, config_key in env_mapping.items():
        value = os.getenv(env_key)
        if value is not None:
            # 布尔值转换
            if value.lower() in ("true", "1", "yes"):
                config[config_key] = True
            elif value.lower() in ("false", "0", "no"):
                config[config_key] = False
            else:
                config[config_key] = value

    return config


def _load_dotenv() -> None:
    """加载 .env 文件到环境变量。"""
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except ImportError:
        pass  # python-dotenv 未安装则跳过


def _load_yaml(path: str) -> dict[str, Any] | None:
    """加载 YAML 配置文件。

    Args:
        path: 文件路径

    Returns:
        解析后的字典，文件不存在时返回 None

    Raises:
        ConfigError: YAML 解析失败
    """
    file_path = Path(path)
    if not file_path.exists():
        return None

    try:
        import yaml

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except ImportError:
        raise ConfigError("请安装 pyyaml: pip install pyyaml")
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML 解析失败 ({path}): {e}")
    except OSError as e:
        raise ConfigError(f"配置文件读取失败 ({path}): {e}")
