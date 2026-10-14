"""全局 AI 配置加载器。

项目内所有 AI 相关配置统一从这里读取，业务代码不得再自行硬编码模型名、
base_url 或密钥。

配置优先级（高 → 低）：
    1. 环境变量          DASHSCOPE_API_KEY、WEBIDE_AI_MODEL、WEBIDE_AI_BASE_URL 等
    2. config/ai_config.local.json   本地覆盖（已 gitignore，用于存放真实密钥）
    3. config/ai_config.json         仓库内默认配置（api_key 留空）

维护方式：
    - 更换密钥 / 模型 / 端点，只需修改 config/ai_config.json
      或（推荐，避免误提交密钥）修改 config/ai_config.local.json
    - 无需改动任何 Python 代码

用法：
    from config import get_ai_config

    cfg = get_ai_config()
    cfg["api_key"], cfg["default_model"], cfg["base_url"]
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_CONFIG_PATH = os.path.join(CONFIG_DIR, 'ai_config.json')
LOCAL_CONFIG_PATH = os.path.join(CONFIG_DIR, 'ai_config.local.json')

# 默认值：任何一项缺失时兜底，保证调用方拿到的字典结构稳定
DEFAULT_CONFIG = {
    'enabled': True,
    'provider': 'dashscope',
    'default_model': 'qwen-plus',
    'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'api_key': '',
    'generation': {
        'temperature': 0.7,
        'max_tokens': 2048,
    },
    'request_timeout': 60,
    'max_context_messages': 20,
    'available_models': [],
}

# 环境变量 → 配置字段的映射
ENV_OVERRIDES = {
    'DASHSCOPE_API_KEY': 'api_key',
    'WEBIDE_AI_MODEL': 'default_model',
    'WEBIDE_AI_BASE_URL': 'base_url',
    'WEBIDE_AI_MAX_MESSAGES': 'max_context_messages',
    'WEBIDE_AI_TIMEOUT': 'request_timeout',
}

_cache = None


def _read_json(path):
    """读取 JSON 文件；不存在或格式错误时返回空字典并记录日志"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"AI 配置文件解析失败 {path}: {e}")
        return {}


def _deep_merge(base, override):
    """递归合并字典，override 优先"""
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env(cfg):
    """用环境变量覆盖配置项，空字符串不覆盖"""
    for env_name, field in ENV_OVERRIDES.items():
        raw = os.environ.get(env_name)
        if raw is None or not str(raw).strip():
            continue

        value = str(raw).strip()
        current = cfg.get(field)
        if isinstance(current, bool):
            value = value.lower() in ('1', 'true', 'yes', 'on')
        elif isinstance(current, int):
            try:
                value = int(value)
            except ValueError:
                logger.warning(f"环境变量 {env_name}={raw!r} 不是整数，已忽略")
                continue
        cfg[field] = value
    return cfg


def _strip_meta(cfg):
    """去掉以下划线开头的说明性字段，避免泄漏到接口响应"""
    return {k: v for k, v in cfg.items() if not k.startswith('_')}


def load_ai_config():
    """加载并合并 AI 配置（不缓存），返回完整字典"""
    cfg = dict(DEFAULT_CONFIG)
    cfg = _deep_merge(cfg, _strip_meta(_read_json(BASE_CONFIG_PATH)))
    cfg = _deep_merge(cfg, _strip_meta(_read_json(LOCAL_CONFIG_PATH)))
    cfg = _apply_env(cfg)
    return cfg


def get_ai_config():
    """获取缓存的 AI 配置"""
    global _cache
    if _cache is None:
        _cache = load_ai_config()
    return _cache


def reload_ai_config():
    """清空缓存并重新加载（修改配置文件后调用，无需重启）"""
    global _cache
    _cache = None
    return get_ai_config()


def get_api_key():
    """获取 API 密钥；未配置时返回空字符串"""
    return str(get_ai_config().get('api_key') or '').strip()


def is_ai_configured():
    """AI 功能是否可用（已启用且已配置密钥）"""
    cfg = get_ai_config()
    return bool(cfg.get('enabled')) and bool(get_api_key())


def describe_missing_config():
    """返回人类可读的配置缺失说明，用于接口错误提示"""
    cfg = get_ai_config()
    if not cfg.get('enabled'):
        return 'AI 功能已在 config/ai_config.json 中被禁用（enabled=false）'
    if not get_api_key():
        return ('AI 服务未配置密钥：请在 config/ai_config.local.json 中设置 api_key，'
                '或设置环境变量 DASHSCOPE_API_KEY')
    return ''
