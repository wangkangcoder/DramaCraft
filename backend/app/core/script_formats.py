from __future__ import annotations

import re
from typing import Any

DEFAULT_SCRIPT_FORMAT = "movie"

SCRIPT_FORMATS: dict[str, dict[str, Any]] = {
    "movie": {
        "label": "电影",
        "acts": ["第一幕", "第二幕", "第三幕"],
        "outline_sections": [
            ("第一幕", "开端（建置、触发事件）"),
            ("第二幕", "发展（对抗、冲突升级）"),
            ("第三幕", "结局（高潮、解决）"),
        ],
    },
    "series": {
        "label": "电视/连续剧",
        "acts": ["第一幕", "第二幕", "第三幕", "第四幕"],
        "outline_sections": [
            ("第一幕", "交代情况 + 抛出问题"),
            ("第二幕", "开始行动 + 遇到麻烦"),
            ("第三幕", "矛盾激化 + 陷入绝境"),
            ("第四幕", "解决危机 + 留下新悬念"),
        ],
    },
    "micro": {
        "label": "短/微短剧",
        "acts": ["第一幕", "第二幕"],
        "outline_sections": [
            ("第一幕", "危机开局、强冲突"),
            ("第二幕", "解决打脸、爽点爆发"),
        ],
    },
}

SCRIPT_FORMAT_ALIASES = {
    "movie": "movie",
    "film": "movie",
    "电影": "movie",
    "series": "series",
    "tv": "series",
    "电视": "series",
    "连续剧": "series",
    "电视剧": "series",
    "电视/连续剧": "series",
    "电视/连续句": "series",
    "micro": "micro",
    "short": "micro",
    "短剧": "micro",
    "微短剧": "micro",
    "短/微短剧": "micro",
}


def normalize_script_format(value: str | None = None) -> str:
    cleaned = str(value or "").strip()
    return SCRIPT_FORMAT_ALIASES.get(cleaned, DEFAULT_SCRIPT_FORMAT)


def get_script_format_config(value: str | None = None) -> dict[str, Any]:
    return SCRIPT_FORMATS[normalize_script_format(value)]


def get_script_format_label(value: str | None = None) -> str:
    return str(get_script_format_config(value)["label"])


def get_act_sequence(value: str | None = None) -> list[str]:
    return list(get_script_format_config(value)["acts"])


def get_outline_sections(value: str | None = None) -> list[tuple[str, str]]:
    return list(get_script_format_config(value)["outline_sections"])


def get_last_act_label(value: str | None = None) -> str:
    acts = get_act_sequence(value)
    return acts[-1] if acts else ""


def get_act_index(label: str, value: str | None = None) -> int:
    acts = get_act_sequence(value)
    try:
        return acts.index(str(label or "").strip()) + 1
    except ValueError:
        return 0


def get_next_act_label(label: str, value: str | None = None) -> str:
    acts = get_act_sequence(value)
    index = get_act_index(label, value)
    return acts[index] if 0 < index < len(acts) else ""


def build_act_label_pattern(value: str | None = None) -> str:
    labels = sorted(get_act_sequence(value), key=len, reverse=True)
    if not labels:
        return r"(第一幕|第二幕|第三幕)"
    return "(" + "|".join(re.escape(label) for label in labels) + ")"


def build_all_act_label_pattern() -> str:
    labels = sorted({label for item in SCRIPT_FORMATS.values() for label in item["acts"]}, key=len, reverse=True)
    return "(" + "|".join(re.escape(label) for label in labels) + ")"
