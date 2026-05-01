import json
from pathlib import Path
from threading import RLock

from app.core.config import settings

RUNTIME_SETTINGS_PATH = Path(__file__).resolve().parents[2] / "runtime_ai_settings.json"
_SETTINGS_LOCK = RLock()

PROVIDER_OPTIONS = {
    "zhipu": {
        "label": "智谱 GLM",
        "models": ["glm-4-plus", "glm-4-air", "glm-4-flash"],
        "default_model": "glm-4-plus",
    },
    "openai": {
        "label": "OpenAI",
        "models": ["gpt-4o", "gpt-4.1-mini"],
        "default_model": "gpt-4o",
    },
    "deepseek": {
        "label": "DeepSeek",
        "models": ["deepseek-v4-pro", "deepseek-v4-flash"],
        "default_model": "deepseek-v4-pro",
    },
}

SAFETY_OPTIONS = {
    "tencent": "腾讯安全云策略",
    "basic": "基础规则引擎",
    "off": "关闭安全审核",
}


def _clamp_float(value, default, minimum=0.0, maximum=1.0):
    try:
        return max(minimum, min(maximum, float(value)))
    except (TypeError, ValueError):
        return default


def _default_settings():
    return {
        "model_base": "deepseek",
        "zhipu_model": PROVIDER_OPTIONS["zhipu"]["default_model"],
        "openai_model": PROVIDER_OPTIONS["openai"]["default_model"],
        "deepseek_model": PROVIDER_OPTIONS["deepseek"]["default_model"],
        "temperature": 0.75,
        "top_p": 0.9,
        "safety_provider": "tencent",
        "zhipu_api_key": settings.ZHIPUAI_API_KEY or "",
        "openai_api_key": settings.OPENAI_API_KEY or "",
        "deepseek_api_key": settings.DEEPSEEK_API_KEY or "",
    }


def _normalize_settings(raw):
    defaults = _default_settings()
    data = defaults | (raw or {})

    model_base = str(data.get("model_base") or defaults["model_base"]).strip().lower()
    if model_base not in PROVIDER_OPTIONS:
        model_base = defaults["model_base"]
    data["model_base"] = model_base

    for provider, config in PROVIDER_OPTIONS.items():
        model_key = f"{provider}_model"
        model_value = str(data.get(model_key) or config["default_model"]).strip()
        if model_value not in config["models"]:
            model_value = config["default_model"]
        data[model_key] = model_value

    safety_provider = str(data.get("safety_provider") or defaults["safety_provider"]).strip().lower()
    if safety_provider not in SAFETY_OPTIONS:
        safety_provider = defaults["safety_provider"]
    data["safety_provider"] = safety_provider

    data["temperature"] = _clamp_float(data.get("temperature"), defaults["temperature"])
    data["top_p"] = _clamp_float(data.get("top_p"), defaults["top_p"])

    for key_name in ("zhipu_api_key", "openai_api_key", "deepseek_api_key"):
        value = data.get(key_name, "")
        data[key_name] = value.strip() if isinstance(value, str) else ""

    return data


def _read_settings():
    if not RUNTIME_SETTINGS_PATH.exists():
        return _default_settings()

    try:
        with RUNTIME_SETTINGS_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return _default_settings()

    return _normalize_settings(data)


def _write_settings(data):
    RUNTIME_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RUNTIME_SETTINGS_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def ensure_runtime_settings_file():
    with _SETTINGS_LOCK:
        current = _read_settings()
        if not RUNTIME_SETTINGS_PATH.exists():
            _write_settings(current)
        return current


def load_runtime_settings(include_secrets=False):
    with _SETTINGS_LOCK:
        current = ensure_runtime_settings_file()
    return serialize_runtime_settings(current, include_secrets=include_secrets)


def save_runtime_settings(payload):
    payload = payload or {}

    with _SETTINGS_LOCK:
        current = _read_settings()
        merged = current.copy()

        for key_name in (
            "model_base",
            "zhipu_model",
            "openai_model",
            "deepseek_model",
            "temperature",
            "top_p",
            "safety_provider",
        ):
            if key_name in payload and payload[key_name] is not None:
                merged[key_name] = payload[key_name]

        for key_name in ("zhipu_api_key", "openai_api_key", "deepseek_api_key"):
            incoming = payload.get(key_name)
            if isinstance(incoming, str) and incoming.strip():
                merged[key_name] = incoming.strip()

        normalized = _normalize_settings(merged)
        _write_settings(normalized)

    return serialize_runtime_settings(normalized, include_secrets=False)


def _mask_secret(value):
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(4, len(value) - 8)}{value[-4:]}"


def resolve_provider_model(runtime_settings):
    provider = runtime_settings["model_base"]
    return runtime_settings.get(f"{provider}_model") or PROVIDER_OPTIONS[provider]["default_model"]


def provider_has_key(runtime_settings):
    provider = runtime_settings["model_base"]
    return bool(runtime_settings.get(f"{provider}_api_key"))


def serialize_runtime_settings(runtime_settings, include_secrets=False):
    data = _normalize_settings(runtime_settings)
    provider = data["model_base"]
    effective_model = resolve_provider_model(data)

    response = {
        "model_base": provider,
        "zhipu_model": data["zhipu_model"],
        "openai_model": data["openai_model"],
        "deepseek_model": data["deepseek_model"],
        "temperature": data["temperature"],
        "top_p": data["top_p"],
        "safety_provider": data["safety_provider"],
        "provider_options": PROVIDER_OPTIONS,
        "safety_options": SAFETY_OPTIONS,
        "effective": {
            "provider": provider,
            "provider_label": PROVIDER_OPTIONS[provider]["label"],
            "model": effective_model,
            "temperature": data["temperature"],
            "top_p": data["top_p"],
            "safety_provider": data["safety_provider"],
            "safety_label": SAFETY_OPTIONS[data["safety_provider"]],
            "provider_ready": provider_has_key(data),
        },
        "key_status": {
            "zhipu_configured": bool(data["zhipu_api_key"]),
            "openai_configured": bool(data["openai_api_key"]),
            "deepseek_configured": bool(data["deepseek_api_key"]),
        },
        "masked_keys": {
            "zhipu_api_key": _mask_secret(data["zhipu_api_key"]),
            "openai_api_key": _mask_secret(data["openai_api_key"]),
            "deepseek_api_key": _mask_secret(data["deepseek_api_key"]),
        },
    }

    if include_secrets:
        response["secrets"] = {
            "zhipu_api_key": data["zhipu_api_key"],
            "openai_api_key": data["openai_api_key"],
            "deepseek_api_key": data["deepseek_api_key"],
        }

    return response


def get_effective_generation_settings(overrides=None):
    overrides = overrides or {}
    current = load_runtime_settings(include_secrets=True)
    base = {
        "provider": current["model_base"],
        "temperature": current["temperature"],
        "top_p": current["top_p"],
        "safety_provider": current["safety_provider"],
    }

    explicit_model = overrides.get("model")
    if explicit_model:
        explicit_model = str(explicit_model).strip()
        for provider, config in PROVIDER_OPTIONS.items():
            if explicit_model in config["models"]:
                base["provider"] = provider
                base["model"] = explicit_model
                break
    else:
        base["model"] = resolve_provider_model(current)

    if "temperature" in overrides and overrides["temperature"] is not None:
        base["temperature"] = _clamp_float(overrides["temperature"], current["temperature"])
    if "top_p" in overrides and overrides["top_p"] is not None:
        base["top_p"] = _clamp_float(overrides["top_p"], current["top_p"])
    if "safety_provider" in overrides and overrides["safety_provider"]:
        provider = str(overrides["safety_provider"]).strip().lower()
        if provider in SAFETY_OPTIONS:
            base["safety_provider"] = provider

    if "model" not in base:
        provider = base["provider"]
        base["model"] = current.get(f"{provider}_model") or PROVIDER_OPTIONS[provider]["default_model"]

    base["api_key"] = current["secrets"].get(f"{base['provider']}_api_key", "")
    base["provider_label"] = PROVIDER_OPTIONS[base["provider"]]["label"]
    base["safety_label"] = SAFETY_OPTIONS[base["safety_provider"]]
    base["provider_ready"] = bool(base["api_key"])
    return base
