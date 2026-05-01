import json
import math
import re
from difflib import SequenceMatcher
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.ai import enforce_script_labels, generate_clean_content, generate_clean_content_with_meta
from app.core.script_formats import (
    DEFAULT_SCRIPT_FORMAT,
    build_act_label_pattern,
    build_all_act_label_pattern,
    get_act_index,
    get_act_sequence,
    get_last_act_label,
    get_next_act_label,
    get_script_format_label,
    normalize_script_format,
)
from app.core.story_constraints import (
    CLUE_TERMS,
    MISSION_VERBS,
    RELATION_TERMS,
    ROLE_SUFFIXES,
    SETTING_SUFFIXES,
    build_story_guardrail_block,
    evaluate_story_alignment,
    extract_story_anchor_groups,
)
from app.models.neo4j_db import neo4j_client

router = APIRouter()
ACT_LABEL_PATTERN = build_all_act_label_pattern()


def _build_generation_review_validation(
    *,
    is_valid: bool,
    reason: str = "",
    corrected: bool = False,
    accepted_with_issues: bool = False,
) -> dict[str, Any]:
    message = (reason or "").strip()
    hard_errors = []
    soft_warnings = []
    if message and not is_valid:
        hard_errors.append(
            {
                "description": message,
                "fix_instruction": "可先保留当前正文，再使用“一键生成修改建议”继续优化这一场。",
            }
        )

    if accepted_with_issues and hard_errors:
        soft_warnings = hard_errors
        hard_errors = []

    return {
        "is_valid": is_valid,
        "hard_errors": hard_errors,
        "soft_warnings": soft_warnings,
        "metrics": {},
        "corrected": corrected,
        "accepted_with_issues": accepted_with_issues,
    }

ENDING_KEYWORDS = [
    "结局",
    "结尾",
    "尾声",
    "余韵",
    "揭晓",
    "落幕",
    "收束",
    "终于",
    "最后",
    "告别",
    "代价",
    "终章",
    "尘埃落定",
]

FORESHADOW_KEYWORDS = [
    "怀表",
    "录音",
    "旧照片",
    "坐标",
    "钥匙",
    "求救信号",
    "日志",
    "芯片",
    "信号",
    "手机",
    "门禁卡",
    "纸条",
    "录像",
    "档案",
    "U盘",
]

OUTLINE_STOPWORDS = {
    "第一幕",
    "第二幕",
    "第三幕",
    "结局",
    "结尾",
    "高潮",
    "余韵",
    "场景",
    "剧情",
    "故事",
    "主角",
    "角色",
    "人物",
    "冲突",
    "推进",
    "发展",
    "收束",
    "完成",
    "最终",
    "开始",
    "因为",
    "所以",
    "以及",
}

INTERNAL_SCAFFOLD_PREFIXES = (
    "上一场位于：",
    "当前目标：",
    "校验备注：",
    "推进说明：",
    "关键对白：",
    "动作描述：",
    "承接上节：",
    "承接上场：",
)

INTERNAL_SCAFFOLD_HEADINGS = {
    "承接上场",
    "承接上节",
    "动作描述",
    "推进说明",
    "关键对白",
}

INTERNAL_SCAFFOLD_FRAGMENTS = (
    "没有停留在上一场的情绪里",
    "局势因此发生了不可逆的变化",
    "埋下了更具体的后果",
    "没有真正推进当前应写的大纲节点",
    "这一次，我们不能再原地打转了。",
)


def _normalize_act_label(label: str) -> str:
    return str(label or "").strip()


def _ordered_unique_labels(labels: list[str]) -> list[str]:
    ordered: list[str] = []
    for label in labels:
        normalized = _normalize_act_label(label)
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return ordered


def _next_act_label_after(label: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> str:
    return get_next_act_label(label, script_format)


def _extract_written_act_labels(text: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> list[str]:
    cleaned = _normalize_script(text)
    if not cleaned:
        return []

    act_label_pattern = build_act_label_pattern(script_format)
    labels = [
        _normalize_act_label(match.group(1))
        for match in re.finditer(
            rf"^{act_label_pattern}[·.、 ]?第[一二三四五六七八九十百零\d]+节$",
            cleaned,
            flags=re.MULTILINE,
        )
    ]
    return _ordered_unique_labels(labels)


def _count_non_whitespace(text: str) -> int:
    return len(re.sub(r"\s+", "", _normalize_script(text)))


def _build_requirement_text(requirements: dict[str, Any]) -> str:
    req_text = (requirements.get("content") or "").strip()
    if req_text:
        return req_text

    title = requirements.get("title", "")
    theme = requirements.get("theme", "")
    audience = requirements.get("audience", "")
    world_setting = requirements.get("world_setting", {}) or {}
    characters = requirements.get("characters", []) or []

    character_lines = []
    for character in characters:
        if not isinstance(character, dict):
            continue
        name = character.get("name", "")
        role = character.get("role", "")
        arc = character.get("arc", "")
        if name or role or arc:
            character_lines.append(f"{name}（{role}）：{arc}".strip())

    parts = [
        f"项目标题：{title}" if title else "",
        f"故事主题：{theme}" if theme else "",
        f"目标受众：{audience}" if audience else "",
        f"世界时间：{world_setting.get('time', '')}" if world_setting.get("time") else "",
        f"世界规则：{world_setting.get('rules', '')}" if world_setting.get("rules") else "",
        f"核心冲突：{world_setting.get('conflict', '')}" if world_setting.get("conflict") else "",
        "角色列表：\n" + "\n".join(character_lines) if character_lines else "",
    ]
    return "\n".join(part for part in parts if part)


def _normalize_script(text: str) -> str:
    cleaned = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[*#`_]+", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _looks_like_dialogue_speaker(line: str) -> bool:
    return bool(re.fullmatch(r"[\u4e00-\u9fff]{2,6}", (line or "").strip()))


def _is_internal_scaffold_line(line: str) -> bool:
    stripped = (line or "").strip()
    if not stripped:
        return False
    if stripped in INTERNAL_SCAFFOLD_HEADINGS:
        return True
    if any(stripped.startswith(prefix) for prefix in INTERNAL_SCAFFOLD_PREFIXES):
        return True
    return any(fragment in stripped for fragment in INTERNAL_SCAFFOLD_FRAGMENTS)


def _contains_internal_scaffolding(text: str) -> bool:
    return any(_is_internal_scaffold_line(line) for line in _normalize_script(text).split("\n"))


def _strip_internal_scaffolding(text: str) -> str:
    normalized = _normalize_script(text)
    if not normalized:
        return ""

    kept_lines: list[str] = []
    for raw_line in normalized.split("\n"):
        stripped = raw_line.strip()
        if _is_internal_scaffold_line(stripped):
            if kept_lines and _looks_like_dialogue_speaker(kept_lines[-1]):
                kept_lines.pop()
            continue
        kept_lines.append(raw_line.rstrip())

    return _normalize_script("\n".join(kept_lines))


def _normalize_match_text(text: str) -> str:
    normalized = _normalize_script(text)
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(r"[，。！？；：、“”‘’（）《》【】\[\]\(\)\-—,.!?:;\"'·]", "", normalized)
    return normalized


def _clean_outline_line(raw_line: str) -> str:
    line = (raw_line or "").strip()
    line = re.sub(r"^[\-\*\d\.\s、]+", "", line)
    return line.strip("：: ")


def _detect_outline_section_label(line: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> str:
    if not line:
        return ""

    for act_label in get_act_sequence(script_format):
        if act_label in line:
            return act_label
    return ""


def _strip_outline_section_heading(line: str, section_label: str) -> str:
    if not line or not section_label:
        return line

    return re.sub(rf"^{re.escape(section_label)}[：:\s-]*", "", line).strip()


def _looks_like_outline_heading(line: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> bool:
    stripped = (line or "").strip("：: ")
    if not stripped:
        return True

    if stripped in {"剧情大纲", "故事大纲", "分幕大纲", "分集大纲"}:
        return True

    if stripped in set(get_act_sequence(script_format)):
        return True

    if re.fullmatch(r"第\s*[一二三四五六七八九十百零\d]+\s*幕", stripped):
        return True

    return False


def _extract_keyword_matches(reference: str, text: str, limit: int = 6) -> tuple[list[str], list[str], float]:
    keywords = _extract_focus_keywords(reference, limit=limit)
    if not keywords:
        return [], [], 0.0

    matched = [keyword for keyword in keywords if keyword in text]
    coverage = len(matched) / len(keywords)
    return keywords, matched, coverage


def _extract_scene_blocks(text: str) -> list[str]:
    cleaned = _normalize_script(text)
    if not cleaned:
        return []

    markers = list(re.finditer(r"^(?:第\s*[一二三四五六七八九十百零\d]+\s*场|内景|外景)", cleaned, flags=re.MULTILINE))
    if not markers:
        return [cleaned]

    blocks: list[str] = []
    for index, match in enumerate(markers):
        start = match.start()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(cleaned)
        block = cleaned[start:end].strip()
        if block:
            blocks.append(block)
    return blocks


def _extract_scene_heading_from_block(scene_block: str) -> str:
    lines = [line.strip() for line in _normalize_script(scene_block).split("\n") if line.strip()]
    for line in lines:
        if line.startswith(("内景", "外景")):
            return line
    for line in lines:
        if re.match(r"^第\s*[一二三四五六七八九十百零\d]+\s*场", line):
            return line
    return lines[0] if lines else ""


def _scene_similarity(left: str, right: str) -> float:
    left_text = _normalize_match_text(left)
    right_text = _normalize_match_text(right)
    if not left_text or not right_text:
        return 0.0
    return SequenceMatcher(None, left_text[:1800], right_text[:1800]).ratio()


def _shared_line_count(left: str, right: str) -> int:
    left_lines = {
        line.strip()
        for line in _normalize_script(left).split("\n")
        if len(line.strip()) >= 8 and not re.match(rf"^{ACT_LABEL_PATTERN}", line.strip())
    }
    right_lines = {
        line.strip()
        for line in _normalize_script(right).split("\n")
        if len(line.strip()) >= 8 and not re.match(rf"^{ACT_LABEL_PATTERN}", line.strip())
    }
    return len(left_lines & right_lines)


def _detect_recent_repetition(content: str, candidate: Optional[str] = None) -> dict[str, Any]:
    scene_blocks = _extract_scene_blocks(content)
    if candidate:
        target_block = _normalize_script(candidate)
        reference_blocks = scene_blocks[-3:]
    else:
        if len(scene_blocks) < 2:
            return {"repetition_detected": False, "reason": "", "similarity": 0.0}
        target_block = scene_blocks[-1]
        reference_blocks = scene_blocks[-4:-1]

    target_heading = _extract_scene_heading_from_block(target_block)
    max_similarity = 0.0
    reasons: list[str] = []

    for block in reference_blocks:
        similarity = _scene_similarity(target_block, block)
        shared_lines = _shared_line_count(target_block, block)
        same_heading = bool(target_heading and target_heading == _extract_scene_heading_from_block(block))
        max_similarity = max(max_similarity, similarity)

        if similarity >= 0.78:
            reasons.append(f"与最近场次文本相似度过高（{similarity:.2f}）")
        elif same_heading and similarity >= 0.58:
            reasons.append("沿用了几乎相同的场景标题和推进方式")
        elif shared_lines >= 3:
            reasons.append("重复复用了最近场次的对白或动作描述")

    return {
        "repetition_detected": bool(reasons),
        "reason": reasons[0] if reasons else "",
        "similarity": max_similarity,
    }


def _build_recent_scene_digest(content: str, limit: int = 3) -> str:
    scenes = _extract_scene_blocks(content)[-limit:]
    if not scenes:
        return ""

    digest_lines: list[str] = []
    for scene in scenes:
        heading = _extract_scene_heading_from_block(scene) or "最近场次"
        keywords = "、".join(_extract_focus_keywords(scene, limit=5)[:4]) or "无"
        digest_lines.append(f"- {heading} | 关键词：{keywords}")

    return "\n".join(digest_lines)


def _build_outline_digest(items: list[dict[str, Any]], empty_text: str, limit: int = 3) -> str:
    if not items:
        return empty_text

    digest_lines: list[str] = []
    for item in items[:limit]:
        section = item.get("section") or "剧情推进"
        text = item.get("text") or ""
        digest_lines.append(f"- {section}：{text}")
    return "\n".join(digest_lines)


def _resolve_next_act_context(
    outline: str,
    content: str,
    start_scene_index: int,
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    outline_progress = _extract_outline_progress(outline, content, script_format=script_format)
    pending_items = outline_progress.get("pending_items", [])
    covered_items = outline_progress.get("covered_items", [])
    written_act_labels = _extract_written_act_labels(content, script_format)
    act_sequence = get_act_sequence(script_format)
    last_act_label = get_last_act_label(script_format)

    act_label = ""
    if written_act_labels:
        act_label = _next_act_label_after(written_act_labels[-1], script_format) or written_act_labels[-1]
    elif pending_items:
        act_label = _normalize_act_label(pending_items[0].get("section") or "")
    else:
        act_label = _get_fallback_act_label(start_scene_index, script_format)

    if not act_label:
        act_label = act_sequence[0] if act_sequence else "第一幕"

    act_pending_items = [
        item for item in pending_items if _normalize_act_label(item.get("section") or "") == act_label
    ]
    act_completed_items = [
        item for item in covered_items if _normalize_act_label(item.get("section") or "") == act_label
    ]

    next_act_label = _next_act_label_after(act_label, script_format)

    current_target = act_pending_items[0]["text"] if act_pending_items else ""
    next_target = act_pending_items[1]["text"] if len(act_pending_items) > 1 else ""

    if outline.strip() and not current_target:
        if act_label == last_act_label:
            current_target = f"完成{last_act_label}的最终收束，回收主要伏笔，交代最后选择带来的后果。"
            next_target = next_target or "本题材所有幕次写完后停止续写。"
        else:
            current_target = f"完整写完{act_label}，让这一幕内部的冲突和推进自然收口。"

    return {
        "outline_progress": outline_progress,
        "act_label": act_label,
        "section_label": act_label,
        "section_index": max(1, len(act_completed_items) + 1),
        "current_target": current_target,
        "next_target": next_target,
        "act_pending_items": act_pending_items,
        "act_completed_items": act_completed_items,
        "next_act_label": next_act_label,
    }


def _coerce_generated_act_format(
    candidate: str,
    act_label: str,
    section_index: int,
    start_scene_index: int,
    fallback_heading: str,
) -> str:
    cleaned = _strip_internal_scaffolding(candidate)
    if not cleaned:
        return ""

    normalized = enforce_script_labels(
        cleaned,
        default_act_label=act_label,
        start_scene_index=start_scene_index,
        max_sections=3,
        single_act=True,
    )
    if not normalized and fallback_heading:
        return f"{act_label}·第{section_index}节\n第{start_scene_index}场\n{fallback_heading}"
    return _normalize_script(normalized)


def _response_was_truncated(response_meta: Optional[dict[str, Any]]) -> bool:
    finish_reason = str((response_meta or {}).get("finish_reason") or "").strip().lower()
    return finish_reason in {"length", "max_tokens"}


def _merge_continuation_text(existing: str, addition: str) -> str:
    base = _normalize_script(existing).rstrip()
    incoming = _normalize_script(addition).strip()
    if not base:
        return incoming
    if not incoming:
        return base
    if incoming in base:
        return base

    overlap = 0
    max_overlap = min(len(base), len(incoming), 240)
    for size in range(max_overlap, 19, -1):
        if base[-size:] == incoming[:size]:
            overlap = size
            break

    if overlap:
        incoming = incoming[overlap:].lstrip()
        if not incoming:
            return base

    separator = ""
    if not base.endswith("\n"):
        if incoming.startswith(("第", "内景", "外景")) or base[-1] in "。！？…）”’》":
            separator = "\n"

    return f"{base}{separator}{incoming}"


def _build_act_continuation_prompt(base_prompt: str, act_label: str, partial_text: str) -> str:
    excerpt = _normalize_script(partial_text)[-2600:]
    return (
        f"{base_prompt}\n\n"
        f"上一次输出在{act_label}中途因为长度限制停下了。下面是已经写出的当前幕正文，请严格接着它继续写完当前这一幕。\n"
        "不要重写前文，不要改写已经生成好的部分，不要跳去下一幕。\n"
        "如果最后一句停在半句，请先把这句话补完整，再继续往下写。\n"
        "只输出这次新增的续写正文，不要解释。\n\n"
        f"已写出的{act_label}正文：\n{excerpt}"
)


def _generate_complete_act_candidate(
    prompt: str,
    *,
    act_label: str,
    section_index: int,
    start_scene_index: int,
    fallback_heading: str,
    max_tokens: int = 4200,
    max_passes: int = 4,
) -> str:
    assembled = ""
    current_prompt = prompt

    for _ in range(max_passes):
        try:
            generated, _, response_meta = generate_clean_content_with_meta(current_prompt, max_tokens=max_tokens)
        except Exception:
            if assembled:
                break
            raise

        chunk = _strip_internal_scaffolding(generated)
        if not chunk.strip():
            if assembled:
                break
            return ""

        assembled = _merge_continuation_text(assembled, chunk)

        if not _response_was_truncated(response_meta):
            break

        current_prompt = _build_act_continuation_prompt(prompt, act_label, assembled)

    return _coerce_generated_act_format(
        assembled,
        act_label=act_label,
        section_index=section_index,
        start_scene_index=start_scene_index,
        fallback_heading=fallback_heading,
    )


def _extract_latest_scene(text: str) -> str:
    lines = [line.strip() for line in _normalize_script(text).split("\n") if line.strip()]
    scene_lines = [line for line in lines if line.startswith(("内景", "外景"))]
    return scene_lines[-1] if scene_lines else "内景 临时空间 夜"


def _extract_recent_prop(text: str) -> str:
    for keyword in ["怀表", "录音", "旧照片", "坐标", "钥匙", "求救信号", "日志", "芯片", "信号"]:
        if keyword in text:
            return keyword
    return "线索"


def _infer_next_scene_title(current_scene: str, scene_index: int) -> str:
    if "港口" in current_scene:
        return "内景 科考船舱 夜"
    if "公寓" in current_scene:
        return "外景 港口 夜"
    if "研究站" in current_scene:
        return "内景 研究站走廊 夜"
    if "船舱" in current_scene:
        return "外景 研究站平台 夜"
    if scene_index % 2 == 0:
        return "外景 暴雨甲板 夜"
    return "内景 临时控制室 夜"


def _extract_next_scene_index(text: str) -> int:
    arabic_hits = [int(item) for item in re.findall(r"第\s*(\d+)\s*场", text)]
    if arabic_hits:
        return max(arabic_hits) + 1

    chinese_map = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    chinese_hits = []
    for item in re.findall(r"第\s*([一二三四五六七八九十])\s*场", text):
        if item in chinese_map:
            chinese_hits.append(chinese_map[item])

    if chinese_hits:
        return max(chinese_hits) + 1

    return len(re.findall(r"^(内景|外景)", text, flags=re.MULTILINE)) + 1


def _build_progression_hint(scene_index: int) -> str:
    hints = [
        "线索由‘异常现象’升级为‘人为布局’，主角开始怀疑内部有人提前布控。",
        "主角不再被动调查，转为主动设局试探同伴，人物关系开始出现裂痕。",
        "旧案与当下危机正式重叠，主角必须在‘保命’和‘揭真相’之间二选一。",
        "前一场留下的道具被反向利用，推动剧情进入不可逆阶段。",
    ]
    return hints[(scene_index - 1) % len(hints)]


def _get_fallback_act_label(scene_index: int, script_format: str = DEFAULT_SCRIPT_FORMAT) -> str:
    act_sequence = get_act_sequence(script_format)
    if not act_sequence:
        return "第一幕"

    if len(act_sequence) == 2:
        return act_sequence[0] if scene_index <= 4 else act_sequence[1]
    if len(act_sequence) == 3:
        if scene_index <= 4:
            return act_sequence[0]
        if scene_index <= 8:
            return act_sequence[1]
        return act_sequence[2]

    if scene_index <= 3:
        return act_sequence[0]
    if scene_index <= 6:
        return act_sequence[1]
    if scene_index <= 9:
        return act_sequence[2]
    return act_sequence[-1]


def _extract_last_dialogue_hint(text: str) -> str:
    lines = [line.strip() for line in _normalize_script(text).split("\n") if line.strip()]
    dialogue_lines = []
    for i in range(len(lines) - 1):
        if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", lines[i]):
            dialogue_lines.append(f"{lines[i]}：{lines[i + 1]}")

    return dialogue_lines[-1] if dialogue_lines else "上一场的对话仍在耳边回响。"


def _extract_outline_anchor(outline: str, act_label: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> str:
    text = _normalize_script(outline)
    if not text:
        return ""

    keywords = [act_label] if act_label in get_act_sequence(script_format) else []
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for idx, line in enumerate(lines):
        if any(key in line for key in keywords):
            anchor_lines = [line]
            for tail in lines[idx + 1 : idx + 4]:
                if any(mark in tail for mark in get_act_sequence(script_format)):
                    break
                anchor_lines.append(tail)
            return "；".join(anchor_lines)

    return lines[0] if lines else ""


def _extract_scene_count(text: str) -> int:
    cleaned = _normalize_script(text)
    numbered_scenes = re.findall(r"^第\s*[一二三四五六七八九十百零\d]+\s*场", cleaned, flags=re.MULTILINE)
    if numbered_scenes:
        return len(numbered_scenes)
    return len(re.findall(r"^(内景|外景)", cleaned, flags=re.MULTILINE))


def _extract_outline_focus_points(outline: str, limit: int = 6) -> list[str]:
    text = _normalize_script(outline)
    if not text:
        return []

    prioritized: list[str] = []
    regular: list[str] = []
    for raw_line in text.split("\n"):
        line = re.sub(r"^[\-\*\d\.\s]+", "", raw_line).strip("：:；; ")
        if not line:
            continue
        target_bucket = prioritized if any(keyword in line for keyword in ENDING_KEYWORDS) else regular
        if line not in target_bucket:
            target_bucket.append(line)

    return (prioritized + regular)[:limit]


def _extract_focus_keywords(text: str, limit: int = 10) -> list[str]:
    cleaned = _normalize_script(text)
    if not cleaned:
        return []

    hits: list[str] = []
    for group in extract_story_anchor_groups(cleaned):
        primary = str(group.get("primary") or "").strip()
        if primary and primary not in OUTLINE_STOPWORDS and primary not in hits:
            hits.append(primary)
        for term in group.get("terms", [])[:2]:
            if term and term not in OUTLINE_STOPWORDS and term not in hits:
                hits.append(term)
        if len(hits) >= limit:
            return hits[:limit]

    focus_terms = sorted(
        set(
            ROLE_SUFFIXES
            + SETTING_SUFFIXES
            + RELATION_TERMS
            + CLUE_TERMS
            + MISSION_VERBS
            + [
                "海港城市",
                "深海实验站",
                "海洋实验站",
                "事故真相",
                "安保主管",
                "失踪",
                "潜入",
                "封锁",
                "调查",
            ]
        ),
        key=len,
        reverse=True,
    )
    focus_terms = [term for term in focus_terms if len(term) >= 2]
    focus_pattern = "|".join(re.escape(term) for term in focus_terms)

    for match in re.finditer(rf"(?:女|男|失踪|封闭|深海|海洋|近未来)?[\u4e00-\u9fff]{{0,4}}(?:{focus_pattern})", cleaned):
        candidate = match.group(0).strip()
        if candidate in OUTLINE_STOPWORDS or len(candidate) < 2:
            continue
        if candidate not in hits:
            hits.append(candidate)
        matched_cores = [term for term in focus_terms if term in candidate and term != candidate]
        for term in matched_cores[:2]:
            if term not in hits:
                hits.append(term)
        if len(hits) >= limit:
            return hits[:limit]

    for verb in MISSION_VERBS:
        for match in re.finditer(rf"{verb}[\u4e00-\u9fff]{{1,8}}", cleaned):
            candidate = match.group(0).strip()
            if len(candidate) < 2 or candidate in hits:
                continue
            hits.append(candidate)
            if len(hits) >= limit:
                return hits[:limit]

    for chunk in re.split(r"[，。！？；：、\s]+", cleaned):
        candidate = chunk.strip()
        if not candidate or candidate in OUTLINE_STOPWORDS:
            continue
        if len(candidate) > 8:
            candidate = candidate[:8]
        if len(candidate) >= 2 and candidate not in hits:
            hits.append(candidate)
        if len(hits) >= limit:
            break

    return hits[:limit]


def _parse_json_object(raw_text: str) -> Optional[dict[str, Any]]:
    if not raw_text:
        return None

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(raw_text[start : end + 1])
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def _looks_like_outline_meta(line: str) -> bool:
    stripped = (line or "").strip()
    if not stripped:
        return False

    meta_keywords = ("建议", "说明", "提示", "要求", "风格", "写法", "格式")
    plot_keywords = ("主角", "反派", "真相", "结局", "高潮", "事故", "线索", "选择", "代价", "冲突")
    return any(keyword in stripped for keyword in meta_keywords) and not any(
        keyword in stripped for keyword in plot_keywords
    )


def _split_outline_segments(line: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> list[str]:
    raw = _normalize_script(line)
    if not raw:
        return []

    primary_parts = [
        part.strip(" ，,；;：:")
        for part in re.split(r"[。！？；]+", raw)
        if part.strip(" ，,；;：:")
    ]
    segments: list[str] = list(primary_parts or [raw])

    cleaned_segments: list[str] = []
    seen: set[str] = set()
    for segment in segments:
        segment = re.sub(r"^(这一幕|本幕|随后|接着|然后|最终|最后)[：:\s]*", "", segment)
        segment = segment.strip(" ，,；;：:")
        if not segment or _looks_like_outline_heading(segment, script_format) or _looks_like_outline_meta(segment):
            continue

        normalized = _normalize_match_text(segment)
        if len(normalized) < 6 or normalized in seen:
            continue

        seen.add(normalized)
        cleaned_segments.append(segment)

    if cleaned_segments:
        return cleaned_segments

    if _looks_like_outline_meta(raw):
        return []
    return [raw] if len(_normalize_match_text(raw)) >= 6 else []


def _extract_outline_items(outline: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> list[dict[str, Any]]:
    text = _normalize_script(outline)
    if not text:
        return []

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    current_section = ""

    for raw_line in text.split("\n"):
        line = _clean_outline_line(raw_line)
        if not line:
            continue

        section_label = _detect_outline_section_label(line, script_format)
        if section_label:
            current_section = section_label
            line = _strip_outline_section_heading(line, section_label)
            if not line:
                continue

        if _looks_like_outline_heading(line, script_format):
            continue

        for segment in _split_outline_segments(line, script_format):
            keywords = _extract_focus_keywords(segment, limit=6)
            if len(keywords) < 2 and len(segment) < 12:
                continue

            key = f"{current_section}|{_normalize_match_text(segment)}"
            if key in seen:
                continue

            seen.add(key)
            items.append({"section": current_section or "剧情推进", "text": segment})

    return _merge_outline_items_by_section(items)


def _merge_outline_items_by_section(
    items: list[dict[str, Any]],
    *,
    max_items_per_section: int = 3,
) -> list[dict[str, Any]]:
    if not items:
        return []

    merged: list[dict[str, Any]] = []
    cursor = 0
    safe_max = max(1, int(max_items_per_section or 3))

    while cursor < len(items):
        section = items[cursor].get("section") or "剧情推进"
        section_items: list[str] = []
        while cursor < len(items) and (items[cursor].get("section") or "剧情推进") == section:
            text = str(items[cursor].get("text") or "").strip()
            if text:
                section_items.append(text)
            cursor += 1

        if len(section_items) <= safe_max:
            merged.extend({"section": section, "text": text} for text in section_items)
            continue

        bucket_count = min(safe_max, len(section_items))
        base_size, extra = divmod(len(section_items), bucket_count)
        offset = 0

        for bucket_index in range(bucket_count):
            size = base_size + (1 if bucket_index < extra else 0)
            chunk = section_items[offset : offset + size]
            offset += size
            if chunk:
                merged.append({"section": section, "text": "；".join(chunk)})

    return merged


def _extract_text_chunks(text: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> list[str]:
    cleaned = _normalize_script(text)
    if not cleaned:
        return []

    chunks: list[str] = []
    for line in cleaned.split("\n"):
        stripped = line.strip()
        if not stripped or _looks_like_outline_heading(stripped, script_format):
            continue

        pieces = [
            chunk.strip(" ，,；;：:")
            for chunk in re.split(r"[。！？；]+", stripped)
            if chunk.strip(" ，,；;：:")
        ]
        for piece in pieces or [stripped]:
            if len(_normalize_match_text(piece)) >= 6:
                chunks.append(piece)

    return chunks or [cleaned]


def _best_chunk_similarity(reference: str, text: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> float:
    reference_norm = _normalize_match_text(reference)
    if not reference_norm:
        return 0.0

    best = 0.0
    for chunk in _extract_text_chunks(text, script_format):
        chunk_norm = _normalize_match_text(chunk)
        if not chunk_norm:
            continue
        best = max(best, SequenceMatcher(None, reference_norm[:180], chunk_norm[:360]).ratio())
        if best >= 0.88:
            break
    return best


def _estimate_segment_match(
    reference: str,
    content: str,
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    keywords, matched, keyword_coverage = _extract_keyword_matches(reference, content)
    similarity = _best_chunk_similarity(reference, content, script_format)
    normalized_item = _normalize_match_text(reference)
    normalized_content = _normalize_match_text(content)
    exact_match = bool(normalized_item and len(normalized_item) >= 10 and normalized_item in normalized_content)

    high_keyword_match = bool(keywords) and len(matched) >= min(2, len(keywords)) and keyword_coverage >= 0.55
    near_full_keyword_match = bool(keywords) and len(matched) >= max(1, len(keywords) - 1) and keyword_coverage >= 0.75
    semantic_match = similarity >= 0.72 and bool(matched)
    covered = exact_match or high_keyword_match or near_full_keyword_match or semantic_match

    return {
        "keywords": keywords,
        "matched_keywords": matched,
        "coverage": keyword_coverage,
        "similarity": similarity,
        "exact_match": exact_match,
        "covered": covered,
    }


def _estimate_outline_item_coverage(
    item_text: str,
    content: str,
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    segment_info = _estimate_segment_match(item_text, content, script_format)
    clauses = [part.strip() for part in re.split(r"[；;]", item_text or "") if part.strip()]
    clause_matches = []
    if len(clauses) >= 2:
        clause_matches = [_estimate_segment_match(clause, content, script_format) for clause in clauses]

    clause_covered_count = sum(1 for item in clause_matches if item.get("covered"))
    clause_required_count = max(2, math.ceil(len(clauses) * 0.6)) if len(clauses) >= 2 else 0
    clause_group_covered = bool(clause_matches) and clause_covered_count >= clause_required_count

    return {
        **segment_info,
        "covered": bool(segment_info.get("covered") or clause_group_covered),
        "clause_count": len(clauses),
        "clause_covered_count": clause_covered_count,
    }


def _is_outline_item_covered(item_text: str, content: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> bool:
    return _estimate_outline_item_coverage(item_text, content, script_format).get("covered", False)


def _extract_outline_progress(
    outline: str,
    content: str,
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    items = _extract_outline_items(outline, script_format)
    covered_items: list[dict[str, Any]] = []
    pending_items: list[dict[str, Any]] = []

    for item in items:
        coverage_info = _estimate_outline_item_coverage(item["text"], content, script_format)
        enriched = {
            **item,
            "keywords": coverage_info["keywords"],
            "matched_keywords": coverage_info["matched_keywords"],
            "coverage": coverage_info["coverage"],
            "similarity": coverage_info["similarity"],
            "exact_match": coverage_info["exact_match"],
        }
        if coverage_info["covered"]:
            covered_items.append(enriched)
        else:
            pending_items.append(enriched)

    section_label = ""
    section_index = 1
    if pending_items:
        section_label = _normalize_act_label(pending_items[0]["section"])
        section_index = len([item for item in covered_items if item["section"] == section_label]) + 1
    elif covered_items:
        section_label = _normalize_act_label(covered_items[-1]["section"])
        section_index = len([item for item in covered_items if item["section"] == section_label])

    return {
        "items": items,
        "covered_items": covered_items,
        "pending_items": pending_items,
        "covered_points": [item["text"] for item in covered_items],
        "pending_points": [item["text"] for item in pending_items],
        "current_target": pending_items[0]["text"] if pending_items else "",
        "next_target": pending_items[1]["text"] if len(pending_items) > 1 else "",
        "section_label": section_label,
        "section_index": max(1, section_index),
        "pending_count": len(pending_items),
    }


def _is_soft_closure_pending(
    item: dict[str, Any],
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> bool:
    section = _normalize_act_label(str(item.get("section") or ""))
    coverage = float(item.get("coverage") or 0.0)
    similarity = float(item.get("similarity") or 0.0)
    matched_keywords = item.get("matched_keywords") or []
    return section == get_last_act_label(script_format) and (
        coverage >= 0.45 or similarity >= 0.68 or len(matched_keywords) >= 2
    )


def _closure_item_is_resolved(item: dict[str, Any]) -> bool:
    coverage = float(item.get("coverage") or 0.0)
    similarity = float(item.get("similarity") or 0.0)
    matched_keywords = item.get("matched_keywords") or []
    return coverage >= 0.6 or similarity >= 0.74 or len(matched_keywords) >= 3


def _build_act_progress_state(
    outline_progress: dict[str, Any],
    content: str,
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    outline_items = outline_progress.get("items", [])
    covered_items = outline_progress.get("covered_items", [])
    pending_items = outline_progress.get("pending_items", [])
    written_act_labels = _extract_written_act_labels(content, script_format)
    act_sequence = get_act_sequence(script_format)

    completed_act_labels: list[str] = []
    for label in act_sequence:
        scoped_items = [item for item in outline_items if _normalize_act_label(item.get("section") or "") == label]
        if scoped_items and not any(_normalize_act_label(item.get("section") or "") == label for item in pending_items):
            completed_act_labels.append(label)

    current_act_label = written_act_labels[-1] if written_act_labels else ""
    if not current_act_label and covered_items:
        current_act_label = _normalize_act_label(covered_items[-1].get("section") or "")

    next_act_label = ""
    if current_act_label:
        next_act_label = _next_act_label_after(current_act_label, script_format)
    else:
        pending_labels = _ordered_unique_labels([item.get("section", "") for item in pending_items])
        next_act_label = pending_labels[0] if pending_labels else ""

    return {
        "written_act_labels": written_act_labels,
        "completed_act_labels": completed_act_labels,
        "current_act_label": current_act_label,
        "next_act_label": next_act_label,
    }


def _extract_first_scene_index(text: str) -> int:
    arabic_hits = [int(item) for item in re.findall(r"第\s*(\d+)\s*场", text)]
    if arabic_hits:
        return min(arabic_hits)

    chinese_map = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    chinese_hits = []
    for item in re.findall(r"第\s*([一二三四五六七八九十])\s*场", text):
        if item in chinese_map:
            chinese_hits.append(chinese_map[item])

    if chinese_hits:
        return min(chinese_hits)

    return 1


def _build_issue_excerpt(text: str, limit: int = 120) -> str:
    cleaned = re.sub(r"\s+", " ", _normalize_script(text))
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."


def _extract_current_act_context(
    content: str,
    outline: str = "",
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    cleaned = _strip_internal_scaffolding(content)
    outline_progress = _extract_outline_progress(outline, cleaned, script_format=script_format)
    act_progress = _build_act_progress_state(outline_progress, cleaned, script_format=script_format)
    current_act_label = (
        act_progress.get("current_act_label")
        or outline_progress.get("section_label")
        or get_act_sequence(script_format)[0]
    )
    current_act_text = cleaned
    previous_content = ""

    header_matches = list(
        re.finditer(
            rf"^{build_act_label_pattern(script_format)}·第[一二三四五六七八九十百零\d]+节\s*$",
            cleaned,
            flags=re.MULTILINE,
        )
    )
    if header_matches:
        labels = [_normalize_act_label(match.group(1)) for match in header_matches]
        current_act_label = labels[-1] or current_act_label
        start_index = len(header_matches) - 1
        while start_index > 0 and labels[start_index - 1] == current_act_label:
            start_index -= 1
        act_start = header_matches[start_index].start()
        previous_content = cleaned[:act_start].strip()
        current_act_text = cleaned[act_start:].strip()

    act_outline_items: list[dict[str, Any]] = []
    covered_act_items: list[dict[str, Any]] = []
    pending_act_items: list[dict[str, Any]] = []
    for item in outline_progress.get("items", []):
        if _normalize_act_label(item.get("section") or "") != current_act_label:
            continue
        coverage_info = _estimate_outline_item_coverage(item["text"], current_act_text, script_format)
        enriched = {
            **item,
            "keywords": coverage_info["keywords"],
            "matched_keywords": coverage_info["matched_keywords"],
            "coverage": coverage_info["coverage"],
            "similarity": coverage_info["similarity"],
            "exact_match": coverage_info["exact_match"],
        }
        act_outline_items.append(enriched)
        if coverage_info["covered"]:
            covered_act_items.append(enriched)
        else:
            pending_act_items.append(enriched)

    next_act_label = act_progress.get("next_act_label") or _next_act_label_after(current_act_label, script_format)
    if next_act_label == current_act_label:
        next_act_label = _next_act_label_after(current_act_label, script_format)

    return {
        "full_content": cleaned,
        "previous_content": previous_content,
        "script_format": script_format,
        "act_label": current_act_label,
        "act_text": current_act_text,
        "outline_progress": outline_progress,
        "act_outline_items": act_outline_items,
        "covered_act_items": covered_act_items,
        "pending_act_items": pending_act_items,
        "next_act_label": next_act_label,
    }


def _extract_json_payload(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
    if not match:
        raise ValueError("模型没有返回可解析的 JSON 对象")
    return json.loads(match.group(0))


def _build_current_act_review_fallback_v2(
    context: dict[str, Any],
    *,
    outline: str = "",
    idea: str = "",
    characters: str = "",
) -> dict[str, Any]:
    act_label = context.get("act_label") or "当前幕"
    act_text = context.get("act_text") or ""
    previous_content = context.get("previous_content") or ""
    outline_items = context.get("act_outline_items") or []
    enhancement_items: list[dict[str, Any]] = []
    polish_items: list[dict[str, Any]] = []

    def append_enhancement(title: str, text: str, reason: str, anchor: str = "") -> None:
        text = str(text or "").strip()
        if not text:
            return
        if any(item.get("text") == text for item in enhancement_items):
            return
        enhancement_items.append(
            {
                "title": str(title or "可补强点").strip() or "可补强点",
                "text": text,
                "reason": str(reason or "").strip(),
                "anchor": str(anchor or "").strip(),
            }
        )

    def append_polish(problem: str, snippet: str, reason: str, suggestion: str = "") -> None:
        problem = str(problem or "").strip()
        if not problem:
            return
        if any(item.get("problem") == problem for item in polish_items):
            return
        polish_items.append(
            {
                "problem": problem,
                "snippet": str(snippet or "").strip() or _build_issue_excerpt(act_text),
                "reason": str(reason or "").strip(),
                "suggestion": str(suggestion or "").strip(),
            }
        )

    if outline_items:
        target_text = str(outline_items[0].get("text") or "").strip()
        if target_text and len(_normalize_script(act_text)) < 1200:
            append_enhancement(
                "推进点还能更落地一点",
                f"可把“{target_text}”写得更具体一点，补一处更明确的动作、反应或信息交换，让这一幕推进更扎实。",
                "当前幕已经在往这个方向推进，但还可以再给一个更可拍、更具体的落点。",
                target_text[:30],
            )

    if previous_content:
        repetition = _detect_recent_repetition(previous_content, act_text)
        if repetition.get("repetition_detected"):
            append_polish(
                "有些信息和前文过近，节奏还能更利落",
                _build_issue_excerpt(act_text),
                repetition.get("reason") or "这段和前文最近的推进过于接近，容易让当前幕显得重复。",
                "可压缩重复交代，把篇幅让给新的动作推进、情绪反应或关系变化。",
            )

    if len(_normalize_script(act_text)) < 600:
        append_enhancement(
            "情绪或动作层还能再补一笔",
            "可在关键转折前后补一处角色反应、动作细节或短对话，让这一幕的情绪起伏更完整。",
            "当前幕信息推进有了，但人物体感还可以再厚一点。",
            act_label,
        )

    if not enhancement_items:
        primary_outline = str(outline_items[0].get("text") or "").strip() if outline_items else ""
        append_enhancement(
            "关键推进还可再具体一点",
            (
                f"可围绕“{primary_outline}”再补一处更明确的动作、信息交换或情绪落点，让这一幕的推进更具象。"
                if primary_outline
                else "可在当前幕补一处更明确的动作、信息交换或情绪落点，让推进更具象。"
            ),
            "即使整体方向正确，当前幕通常仍能在推进落点上再具体一点。",
            primary_outline[:30] if primary_outline else act_label,
        )

    if not polish_items:
        append_polish(
            "可将一处关键叙述写得更具体",
            _build_issue_excerpt(act_text, limit=90),
            "当前幕整体方向没有问题，但这段表达还可以更具画面感和动作指向。",
            "把这段里的动作、停顿、视线或短对话写得更明确，让读者更容易感到现场。",
        )

    return {
        "enhancement": {
            "has_issue": bool(enhancement_items),
            "summary": (
                f"{act_label}还有一些可以继续补强的小地方，优先补最影响现场感和推进感的部分。"
                if enhancement_items
                else f"{act_label}在“还能补什么”这一项上暂时没有明显补强点。"
            ),
            "items": enhancement_items[:4],
        },
        "polish": {
            "has_issue": bool(polish_items),
            "summary": (
                f"{act_label}还有一些句段可以再压缩、提劲或写得更具体。"
                if polish_items
                else f"{act_label}在“哪些句段还能改得更好”这一项上暂时没有明显问题。"
            ),
            "items": polish_items[:4],
        },
        "summary": (
            f"{act_label}整体已经能推进剧情，目前更适合做细节补强和句段优化。"
            if enhancement_items or polish_items
            else f"{act_label}整体比较稳定，暂时没有必须处理的明显优化点。"
        ),
        "next_step": (
            "可继续点击“一键生成优化版本”，系统会围绕这些小优化点只重写当前这一幕。"
            if enhancement_items or polish_items
            else "当前幕整体稳定，可直接继续下一幕，或按需手动润色。"
        ),
    }


def _analyze_current_act_with_model_v2(
    context: dict[str, Any],
    fallback_review: dict[str, Any],
    *,
    idea: str = "",
    characters: str = "",
) -> dict[str, Any]:
    outline_digest = _build_outline_digest(
        context.get("act_outline_items") or [],
        "当前没有提取到可用的大纲节点。",
        limit=4,
    )
    previous_digest = _build_recent_scene_digest(context.get("previous_content") or "", limit=2) or "- 无更早前文"
    fallback_enhancement = "\n".join(
        f"- {item.get('title', '可补强点')}：{item.get('text', '')}"
        for item in (fallback_review.get("enhancement", {}).get("items") or [])
    ) or "- 当前没有明显的补强候选"
    fallback_polish = "\n".join(
        f"- {item.get('problem', '')}：{item.get('reason', '')}"
        for item in (fallback_review.get("polish", {}).get("items") or [])
    ) or "- 当前没有明显的句段优化候选"

    prompt = f"""你是中文剧本优化顾问。

你的任务只有两个：
1. 找出当前幕里“还可以补强什么”，也就是还能再加一点什么、再落地一点什么，能让这一幕更扎实、更有戏。
2. 找出当前幕里“哪些句子或段落还可以改得更好”，也就是表达偏平、节奏略拖、动作反应不够具体、对话还可以更有力的地方。

要求：
- 就沿着这两个方向尽可能找出可优化点。
- 优先给小而准、能直接改进文本质量的建议。
- 不要为了凑数强行制造问题。
- 所有建议都只针对当前这一幕，不讨论下一幕怎么写。

当前幕：{context.get("act_label") or "当前幕"}
本幕对应的大纲要点（仅供判断还能补强什么，不要拿它硬判对错）：
{outline_digest}

前文最近场次（仅供判断承接和重复）：
{previous_digest}

人物设定（仅供把握人物关系与说话方式）：
{characters or "未提供"}

最早核心设定（仅供守住题设，不要扩写）：
{_normalize_script(idea)[:600] or "未提供"}

系统给出的低风险候选提示：
可补强候选：
{fallback_enhancement}

可优化句段候选：
{fallback_polish}

当前这一幕正文：
{context.get("act_text") or ""}

请只返回 JSON：
{{
  "enhancement_summary": "一句话说明当前幕还有哪些地方可以补强；如果没有就写“这一方面暂时没有明显补强点”",
  "enhancement_items": [
    {{
      "title": "补强点标题",
      "text": "具体建议，写明可以加什么或强化什么",
      "reason": "为什么这样改会更好",
      "anchor": "建议落在当前幕哪一段附近，最多30字"
    }}
  ],
  "polish_summary": "一句话说明哪些句段可以改得更好；如果没有就写“这一方面暂时没有明显可优化句段”",
  "polish_items": [
    {{
      "problem": "句段可优化点标题",
      "snippet": "建议修改的原文片段，最多60字",
      "reason": "为什么这段可以改进",
      "suggestion": "建议往哪个方向改"
    }}
  ],
  "summary": "对当前幕整体优化空间的简短总结",
  "next_step": "给用户的下一步建议"
}}

规则：
1. enhancement_items 最多 3 条，polish_items 最多 3 条。
2. 只要当前幕正文不是空的，就至少给 1 条 enhancement 和 1 条 polish，不要返回空数组。
3. 建议必须是小而准、能直接落实到文本里的优化。
4. 不要输出 JSON 之外的任何内容。"""

    raw, _ = generate_clean_content(prompt, max_tokens=1800)
    return _extract_json_payload(raw)


def _merge_current_act_review_v2(
    context: dict[str, Any],
    fallback_review: dict[str, Any],
    model_review: dict[str, Any] | None,
) -> dict[str, Any]:
    act_label = context.get("act_label") or "当前幕"
    enhancement_items: list[dict[str, Any]] = []
    polish_items: list[dict[str, Any]] = []

    def append_enhancement(item: dict[str, Any]) -> None:
        text = str(item.get("text") or "").strip()
        if not text:
            return
        if any(existing.get("text") == text for existing in enhancement_items):
            return
        enhancement_items.append(
            {
                "title": str(item.get("title") or "可补强点").strip() or "可补强点",
                "text": text,
                "reason": str(item.get("reason") or "").strip(),
                "anchor": str(item.get("anchor") or "").strip(),
            }
        )

    def append_polish(item: dict[str, Any]) -> None:
        problem = str(item.get("problem") or "").strip()
        if not problem:
            return
        if any(existing.get("problem") == problem for existing in polish_items):
            return
        polish_items.append(
            {
                "problem": problem,
                "snippet": str(item.get("snippet") or "").strip() or _build_issue_excerpt(context.get("act_text") or ""),
                "reason": str(item.get("reason") or "").strip(),
                "suggestion": str(item.get("suggestion") or "").strip(),
            }
        )

    for item in (model_review or {}).get("enhancement_items", []) or []:
        if isinstance(item, dict):
            append_enhancement(item)
    for item in fallback_review.get("enhancement", {}).get("items", []) or []:
        append_enhancement(item)

    for item in (model_review or {}).get("polish_items", []) or []:
        if isinstance(item, dict):
            append_polish(item)
    for item in fallback_review.get("polish", {}).get("items", []) or []:
        append_polish(item)

    enhancement_summary = str((model_review or {}).get("enhancement_summary") or "").strip()
    if not enhancement_summary:
        enhancement_summary = (
            f"{act_label}还有一些可以继续补强的小地方。"
            if enhancement_items
            else f"{act_label}在“还能补什么”这一项上暂时没有明显补强点。"
        )

    polish_summary = str((model_review or {}).get("polish_summary") or "").strip()
    if not polish_summary:
        polish_summary = (
            f"{act_label}还有一些句段可以再优化一下。"
            if polish_items
            else f"{act_label}在“哪些句段还能改得更好”这一项上暂时没有明显问题。"
        )

    has_issues = bool(enhancement_items or polish_items)
    summary = str((model_review or {}).get("summary") or "").strip()
    if not summary:
        summary = (
            f"{act_label}整体已经能推进剧情，目前更适合做细节补强和句段优化。"
            if has_issues
            else f"{act_label}整体比较稳定，暂时没有必须处理的明显优化点。"
        )

    next_step = str((model_review or {}).get("next_step") or "").strip()
    if not next_step:
        next_step = (
            "可继续点击“一键生成优化版本”，系统会围绕这些优化建议只重写当前这一幕。"
            if has_issues
            else "当前幕整体稳定，可直接继续下一幕，或按需手动润色。"
        )

    enhancement = {
        "has_issue": bool(enhancement_items),
        "summary": enhancement_summary,
        "items": enhancement_items[:4],
    }
    polish = {
        "has_issue": bool(polish_items),
        "summary": polish_summary,
        "items": polish_items[:4],
    }

    return {
        "act_label": act_label,
        "current_act_text": context.get("act_text") or "",
        "has_issues": has_issues,
        "enhancement": enhancement,
        "polish": polish,
        "summary": summary,
        "next_step": next_step,
    }


def _build_current_act_review(
    content: str,
    *,
    outline: str = "",
    idea: str = "",
    characters: str = "",
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    context = _extract_current_act_context(content, outline, script_format=script_format)
    act_label = context.get("act_label") or "当前幕"
    act_text = context.get("act_text") or ""

    if not act_text:
        empty_summary = "当前还没有可分析的幕次正文。"
        return {
            "act_label": act_label,
            "current_act_text": "",
            "has_issues": False,
            "enhancement": {"has_issue": False, "summary": empty_summary, "items": []},
            "polish": {"has_issue": False, "summary": empty_summary, "items": []},
            "summary": empty_summary,
            "next_step": "请先生成当前幕正文，再生成优化建议。",
        }

    fallback_review = _build_current_act_review_fallback_v2(
        context,
        outline=outline,
        idea=idea,
        characters=characters,
    )

    model_review = None
    try:
        model_review = _analyze_current_act_with_model_v2(
            context,
            fallback_review,
            idea=idea,
            characters=characters,
        )
    except Exception:
        model_review = None

    return _merge_current_act_review_v2(
        context,
        fallback_review,
        model_review,
    )


def _build_enhancement_issue_lines_v2(
    items: list[dict[str, Any]] | list[str],
    empty_text: str = "- 这一方面暂时没有明显补强点，保持当前有效推进即可。",
) -> str:
    lines: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            text = str(item.get("text") or "").strip()
            reason = str(item.get("reason") or "").strip()
            anchor = str(item.get("anchor") or "").strip()
            detail = text or title
        else:
            title = ""
            detail = str(item or "").strip()
            reason = ""
            anchor = ""

        if not detail:
            continue

        line = f"- {detail}"
        detail_parts: list[str] = []
        if title and title != detail:
            detail_parts.append(f"标题：{title}")
        if reason:
            detail_parts.append(f"原因：{reason}")
        if anchor:
            detail_parts.append(f"建议位置：{anchor}")
        if detail_parts:
            line = f"{line}；{'；'.join(detail_parts)}"
        lines.append(line)

    return "\n".join(lines) or empty_text


def _build_polish_issue_lines_v2(
    items: list[dict[str, Any]] | list[str],
    empty_text: str = "- 这一方面暂时没有明显可优化句段，保留当前有效表达即可。",
) -> str:
    lines: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            problem = str(item.get("problem") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            reason = str(item.get("reason") or "").strip()
            suggestion = str(item.get("suggestion") or "").strip()
        else:
            problem = str(item or "").strip()
            snippet = ""
            reason = ""
            suggestion = ""

        if not any((problem, snippet, reason, suggestion)):
            continue

        line = f"- {problem or '可优化句段'}"
        detail_parts: list[str] = []
        if snippet:
            detail_parts.append(f"原文片段：{snippet}")
        if reason:
            detail_parts.append(f"原因：{reason}")
        if suggestion:
            detail_parts.append(f"优化方向：{suggestion}")
        if detail_parts:
            line = f"{line}；{'；'.join(detail_parts)}"
        lines.append(line)

    return "\n".join(lines) or empty_text


def _build_current_act_revision_prompt(
    context: dict[str, Any],
    analysis: dict[str, Any],
    *,
    characters: str = "",
    idea: str = "",
) -> str:
    act_label = context.get("act_label") or "当前幕"
    next_act_label = context.get("next_act_label") or "下一幕"
    format_label = get_script_format_label(context.get("script_format") or DEFAULT_SCRIPT_FORMAT)
    outline_digest = _build_outline_digest(
        context.get("act_outline_items") or [],
        "当前没有提取到可用的大纲节点。",
        limit=4,
    )
    covered_digest = _build_outline_digest(
        context.get("covered_act_items") or [],
        "当前幕还没有稳定落地的节点，可在修订时重新组织。",
        limit=3,
    )
    enhancement_section = analysis.get("enhancement") or {}
    polish_section = analysis.get("polish") or {}
    missing_lines = _build_enhancement_issue_lines_v2(enhancement_section.get("items") or [])
    off_outline_lines = _build_polish_issue_lines_v2(polish_section.get("items") or [])
    previous_tail = (context.get("previous_content") or "")[-1800:] or "这是开场，没有更早前文。"

    return f"""你是专业中文编剧，请只重写当前这一幕，让它在不推翻原有走向的前提下更扎实、更有戏、更好读。当前剧本形式题材是“{format_label}”。
下面列出的不是“原则性大错”，而是已经整理好的优化建议。你的任务是把这些建议真正落实到当前这一幕里，不要解释，不要总结，只输出优化后的当前幕正文。
当前幕：{act_label}
下一幕：{next_act_label}
本幕对应的大纲要点（仅供守住这一幕该往哪里推进）：
{outline_digest}

当前这一幕已经比较有效的落点：
{covered_digest}

优化建议 1：当前幕还可以补强什么
{missing_lines}

优化建议 2：哪些句子或段落可以改得更好
{off_outline_lines}

人物设定（仅供承接，不要改人物身份）：
{characters or "沿用当前正文里的人物关系"}

最早核心设定（仅供守住题设，不要扩写说明）：
{_normalize_script(idea)[:800] or "未提供"}

修订要求：
1. 只改当前这一幕，不要改前文，也不要补写下一幕。
2. 这是一次“细节补强 + 句段优化”的修订，不要硬做原则性纠错，不要把文本改成另一场戏。
3. 优先保留当前幕里已经有效的推进、动作和对话，只把需要补强和需要优化的地方改到位。
4. 如果建议里提到“可以再加什么”，就把它自然落进当前幕里；如果提到“哪句还能更好”，就直接把那段改得更具体、更有力度。
5. 改写时保持当前幕和前文的人物关系、冲突方向与叙事承接，不要另起炉灶。
6. 输出必须是可拍摄的剧本正文，不要写“修改说明”“分析”“优化后”等任何解释性文字。
7. 保持中文幕节标题、场次编号、内景/外景标题格式自然清晰。
8. 尽量让人物反应、动作推进和对话力度更具体，而不是只换一些华丽词语。

前文末尾（仅供承接，不要重写）：
{previous_tail}

当前这一幕原文：
{context.get("act_text") or ""}"""


def _revise_current_act(
    content: str,
    *,
    outline: str = "",
    characters: str = "",
    idea: str = "",
    analysis: Optional[dict[str, Any]] = None,
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    context = _extract_current_act_context(content, outline, script_format=script_format)
    act_text = context.get("act_text") or ""
    if not act_text:
        raise ValueError("当前还没有可修订的幕次正文")

    review = analysis if isinstance(analysis, dict) else None
    if not review or review.get("act_label") != context.get("act_label"):
        review = _build_current_act_review(
            content,
            outline=outline,
            idea=idea,
            characters=characters,
            script_format=script_format,
        )

    if not review.get("has_issues"):
        cleaned_content = context.get("full_content") or _strip_internal_scaffolding(content)
        return {
            "act_label": context.get("act_label") or "当前幕",
            "analysis": review,
            "revised_act": act_text,
            "revised_content": cleaned_content,
            "completion": _build_completion_fallback(cleaned_content, outline, script_format=script_format),
            "accepted_with_issues": False,
            "warning": "",
            "generated": False,
        }

    prompt = _build_current_act_revision_prompt(
        context,
        review,
        characters=characters,
        idea=idea,
    )
    act_label = context.get("act_label") or "当前幕"
    start_scene_index = _extract_first_scene_index(act_text) or max(
        1,
        _extract_next_scene_index(context.get("previous_content") or ""),
    )
    fallback_heading = (
        _extract_scene_heading_from_block(_extract_scene_blocks(act_text)[0])
        if _extract_scene_blocks(act_text)
        else _extract_latest_scene(act_text)
    )
    last_failure_reason = "模型没有返回可用的修订版正文"
    last_candidate = ""
    attempt_prompt = prompt

    for attempt in range(2):
        try:
            normalized = _generate_complete_act_candidate(
                attempt_prompt,
                act_label=act_label,
                section_index=1,
                start_scene_index=start_scene_index,
                fallback_heading=fallback_heading,
                max_tokens=4200,
            )
        except Exception:
            normalized = ""

        if not normalized:
            last_failure_reason = "模型没有返回可用的修订版正文"
            if attempt == 0:
                attempt_prompt = (
                    f"{prompt}\n\n注意：上一轮没有返回有效的完整当前幕正文。"
                    "这一次仍然只根据原稿和问题清单重写当前幕，必须直接输出一版新的完整当前幕剧本正文。"
                )
            continue

        last_candidate = _strip_internal_scaffolding(normalized) or normalized
        last_failure_reason = ""
        break

    revised_act = _strip_internal_scaffolding(last_candidate)
    if not revised_act:
        raise ValueError(last_failure_reason or "模型未能生成可用的修订版正文")

    previous_content = context.get("previous_content") or ""
    revised_content = (
        _strip_internal_scaffolding(f"{previous_content}\n\n{revised_act}")
        if previous_content
        else revised_act
    )

    return {
        "act_label": act_label,
        "analysis": review,
        "revised_act": revised_act,
        "revised_content": revised_content,
        "completion": _build_completion_fallback(revised_content, outline, script_format=script_format),
        "accepted_with_issues": False,
        "warning": "",
        "generated": True,
    }


def _build_target_keyword_hint(target: str, empty_text: str = "根据当前节点自然推进") -> str:
    keywords = _extract_focus_keywords(target, limit=4)
    return "、".join(keywords) if keywords else empty_text


def _detect_outline_backtracking(
    candidate: str,
    outline_progress: dict[str, Any],
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    current_target = outline_progress.get("current_target") or ""
    if not current_target:
        return {"backtracking": False, "reason": ""}

    current_eval = _estimate_outline_item_coverage(current_target, candidate, script_format)
    current_strength = max(float(current_eval.get("coverage") or 0.0), float(current_eval.get("similarity") or 0.0))
    strongest_repeat: dict[str, Any] | None = None

    for item in (outline_progress.get("covered_items") or [])[-3:]:
        text = item.get("text") or ""
        if not text:
            continue

        item_eval = _estimate_outline_item_coverage(text, candidate, script_format)
        item_strength = max(float(item_eval.get("coverage") or 0.0), float(item_eval.get("similarity") or 0.0))
        if not item_eval.get("covered") or item_strength < 0.78:
            continue

        if strongest_repeat is None or item_strength > strongest_repeat["strength"]:
            strongest_repeat = {
                "text": text,
                "strength": item_strength,
            }

    if strongest_repeat and strongest_repeat["strength"] >= current_strength + 0.12:
        return {
            "backtracking": True,
            "reason": f"新一幕又把已完成节点写成了核心事件：{strongest_repeat['text']}",
        }

    return {"backtracking": False, "reason": ""}


def _validate_generated_act(
    candidate: str,
    content: str,
    outline_progress: dict[str, Any],
    outline: str = "",
    idea: str = "",
    characters: str = "",
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    if _contains_internal_scaffolding(candidate):
        return {"ok": False, "reason": "新一幕混入了校验备注或动作描述等内部脚手架"}

    cleaned_candidate = _strip_internal_scaffolding(candidate)
    if not cleaned_candidate:
        return {"ok": False, "reason": "新一幕没有返回有效剧本文本"}

    repetition = _detect_recent_repetition(content, cleaned_candidate)
    if repetition.get("repetition_detected"):
        return {"ok": False, "reason": repetition.get("reason") or "新一幕与最近内容重复"}

    backtracking = _detect_outline_backtracking(cleaned_candidate, outline_progress)
    if backtracking.get("backtracking"):
        return {"ok": False, "reason": backtracking.get("reason") or "新一幕回退到了已完成节点"}

    written_act_labels = _extract_written_act_labels(content, script_format)
    first_act_label = get_act_sequence(script_format)[0]
    if written_act_labels:
        target_act_label = _next_act_label_after(written_act_labels[-1], script_format) or written_act_labels[-1]
    else:
        target_act_label = _normalize_act_label(outline_progress.get("section_label") or "")
        if not target_act_label:
            pending_items = outline_progress.get("pending_items", [])
            if pending_items:
                target_act_label = _normalize_act_label(pending_items[0].get("section") or "")
        if not target_act_label:
            target_act_label = first_act_label

    candidate_act_labels = _extract_written_act_labels(cleaned_candidate, script_format)
    if candidate_act_labels and any(label != target_act_label for label in candidate_act_labels):
        return {"ok": False, "reason": f"新一幕越过了当前应写的{target_act_label}，混入了后续幕次"}

    if outline.strip() and outline_progress.get("items"):
        merged_progress = _extract_outline_progress(outline, f"{content}\n\n{cleaned_candidate}", script_format)
        remaining_target_items = [
            item
            for item in merged_progress.get("pending_items", [])
            if _normalize_act_label(item.get("section") or "") == target_act_label
        ]
        if remaining_target_items:
            return {
                "ok": False,
                "reason": f"{target_act_label}写完后仍未完成本幕节点：{remaining_target_items[0].get('text', target_act_label)}",
            }

    if idea.strip():
        alignment = evaluate_story_alignment(cleaned_candidate, idea, stage="script")
        if not alignment.get("is_valid", True):
            missing = alignment.get("required_missing") or alignment.get("missing_groups") or []
            primary = ""
            if missing:
                primary = missing[0].get("primary") or missing[0].get("label") or ""
            return {
                "ok": False,
                "reason": f"新一幕脱离了最早设定，缺少核心锚点：{primary or '题设主线'}",
            }

    if characters.strip():
        expected_names = [name for name in re.findall(r"姓名[:：]\s*([\u4e00-\u9fff]{2,6})", characters) if name]
        if expected_names and not any(name in cleaned_candidate for name in expected_names):
            return {
                "ok": False,
                "reason": f"新一幕没有承接人物设定，缺少核心角色：{expected_names[0]}",
            }

    return {"ok": True, "reason": "", "cleaned": cleaned_candidate}


def _build_completion_fallback(
    content: str,
    outline: str,
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    cleaned = _strip_internal_scaffolding(content)
    outline_progress = _extract_outline_progress(outline, cleaned, script_format)
    act_progress = _build_act_progress_state(outline_progress, cleaned, script_format)
    outline_points = outline_progress.get("items", [])
    scene_count = _extract_scene_count(cleaned)
    tail = cleaned[-1800:]
    final_act_label = get_last_act_label(script_format)

    covered_items = outline_progress.get("covered_items", [])
    pending_items = outline_progress.get("pending_items", [])
    critical_pending_items: list[dict[str, Any]] = []
    soft_pending_items: list[dict[str, Any]] = []
    final_act_reached = final_act_label in act_progress.get("written_act_labels", []) or (
        act_progress.get("current_act_label") == final_act_label
    )

    for item in pending_items:
        if _is_soft_closure_pending(item, script_format):
            soft_pending_items.append(item)
        else:
            critical_pending_items.append(item)

    matched_points = [item["text"] for item in covered_items]
    missing_points = [item["text"] for item in critical_pending_items]
    soft_missing_points = [item["text"] for item in soft_pending_items]
    outline_coverage = round(len(matched_points) / len(outline_points), 2) if outline_points else 0.0
    repetition = _detect_recent_repetition(cleaned)
    closure_ready = not soft_pending_items or all(_closure_item_is_resolved(item) for item in soft_pending_items)

    resolved_threads: list[str] = []
    dangling_threads: list[str] = []
    for keyword in FORESHADOW_KEYWORDS:
        occurrences = len(re.findall(re.escape(keyword), cleaned))
        if occurrences == 0:
            continue
        if keyword in tail:
            resolved_threads.append(keyword)
        elif occurrences == 1:
            dangling_threads.append(keyword)

    ending_reached = final_act_label in act_progress.get("written_act_labels", []) or any(
        keyword in tail for keyword in ENDING_KEYWORDS
    )
    act_count = len(get_act_sequence(script_format))
    minimum_scenes = 2 if act_count <= 2 else 3
    if not outline_points:
        minimum_scenes = max(2, minimum_scenes - 1)
    is_complete = (
        scene_count >= minimum_scenes
        and ending_reached
        and (
            not outline_points
            or (not critical_pending_items and closure_ready and outline_coverage >= 0.88)
        )
        and not dangling_threads
        and not repetition.get("repetition_detected")
    )

    if is_complete:
        reason = f"当前剧本已经完整覆盖大纲主线，并且{final_act_label}完成了收束。"
    elif final_act_reached and missing_points:
        reason = f"当前题材的全部幕次已经生成完成，但还有内容需要修正：{missing_points[0]}"
    elif final_act_reached and soft_missing_points:
        reason = f"当前题材的全部幕次已经生成完成，但{final_act_label}还没有完全收束：{soft_missing_points[0]}"
    elif final_act_reached and dangling_threads:
        reason = f"当前题材的全部幕次已经生成完成，但仍有关键伏笔没有明显回收：{dangling_threads[0]}"
    elif repetition.get("repetition_detected"):
        reason = repetition.get("reason") or "最近几场出现了重复生成，当前不应继续机械续写。"
    elif missing_points:
        reason = f"仍有大纲内容未充分落地：{missing_points[0]}"
    elif soft_missing_points:
        reason = f"{final_act_label}还没有完全收束：{soft_missing_points[0]}"
    elif dangling_threads:
        reason = f"仍有关键伏笔没有明显回收：{dangling_threads[0]}"
    elif not ending_reached:
        reason = f"当前文本还没有进入明确的{final_act_label}收束段落。"
    else:
        reason = "当前剧本还在推进阶段，尚未达到自动完结条件。"

    generation_locked = is_complete or final_act_reached

    return {
        "is_complete": is_complete,
        "reason": reason,
        "scene_count": scene_count,
        "ending_reached": ending_reached,
        "outline_coverage": outline_coverage,
        "matched_points": matched_points[:6],
        "missing_points": missing_points[:6],
        "soft_missing_points": soft_missing_points[:3],
        "resolved_threads": resolved_threads[:6],
        "dangling_threads": dangling_threads[:6],
        "covered_count": len(matched_points),
        "total_outline_items": len(outline_points),
        "current_target": outline_progress.get("current_target", ""),
        "next_target": outline_progress.get("next_target", ""),
        "section_label": outline_progress.get("section_label", ""),
        "current_act_label": act_progress.get("current_act_label", ""),
        "next_act_label": act_progress.get("next_act_label", ""),
        "completed_act_labels": act_progress.get("completed_act_labels", []),
        "written_act_labels": act_progress.get("written_act_labels", []),
        "final_act_reached": final_act_reached,
        "repetition_detected": bool(repetition.get("repetition_detected")),
        "repetition_reason": repetition.get("reason", ""),
        "generation_locked": generation_locked,
        "can_continue": not generation_locked,
        "source": "fallback",
    }


def _build_next_act_prompt(
    content: str,
    outline: str,
    characters: str,
    idea: str = "",
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    cleaned = _strip_internal_scaffolding(content)
    current_scene = _extract_latest_scene(cleaned)
    prop = _extract_recent_prop(cleaned)
    start_scene_index = _extract_next_scene_index(cleaned)
    act_context = _resolve_next_act_context(outline, cleaned, start_scene_index, script_format=script_format)
    act_label = act_context["act_label"]
    section_index = 1
    current_target = act_context["current_target"]
    next_target = act_context["next_target"]
    outline_progress = act_context["outline_progress"]
    act_pending_items = act_context.get("act_pending_items", [])
    act_completed_items = act_context.get("act_completed_items", [])
    next_act_label = act_context.get("next_act_label", "")
    progression_hint = _build_progression_hint(start_scene_index)
    last_dialogue_hint = _extract_last_dialogue_hint(cleaned)
    idea_guardrails = build_story_guardrail_block(idea, "script") if idea.strip() else "若无补充设定，严格沿用人物设定、剧情大纲和已有正文。"
    idea_excerpt = _normalize_script(idea)[:900] if idea.strip() else "未提供额外核心设定原文。"
    recent_scene_digest = _build_recent_scene_digest(cleaned, limit=3)
    covered_digest = _build_outline_digest(act_completed_items[-3:], "本幕暂无已完成节点摘要。", limit=3)
    pending_digest = _build_outline_digest(
        act_pending_items,
        f"{act_label}需根据已有正文自然收口。",
        limit=4,
    )
    remaining_count = len(act_pending_items)
    current_target_keywords = _build_target_keyword_hint(current_target)
    next_target_keywords = _build_target_keyword_hint(next_target, empty_text="根据剧情自然衔接")
    format_label = get_script_format_label(script_format)
    if act_label == get_last_act_label(script_format):
        closure_instruction = f"本次必须完整写完{act_label}，完成主线收束、伏笔回收和最后余韵，不要再开启新的主线。"
    else:
        closure_instruction = f"本次必须把{act_label}完整讲完，写完就停，不要抢写{next_act_label or '后续幕次'}。"
    act_target_line = current_target or f"完整写完{act_label}"

    completed_digest = _build_outline_digest(
        outline_progress.get("covered_items", []),
        "暂无已完成节点，先把当前触发事件落地。",
        limit=4,
    )

    prompt = f"""你是专业中文编剧，请只续写“下一幕”剧本正文，并严格对齐剧情大纲。当前剧本形式题材是“{format_label}”。你现在写的是可拍摄的戏，不是分析、不是流程说明、不是校验备注。
硬性要求：
1. 只输出新增这一幕的正文，不要解释，不要总结，不要重复前文。
2. 这次只允许写{act_label}，不要越过到{next_act_label or '后续幕次'}。
3. {closure_instruction}
4. {act_label}内部最多分 3 节；只有切换到下一节时，才允许再次输出“{act_label}·第2节”这类标签。
5. 同一节内的后续场次不要重复叠加相同的幕节标题，更不要出现“剧情推进·第1节 第4场”这类混合标签。
6. 场次编号必须从第{start_scene_index}场开始顺延，每个“第X场”只能出现一次，严禁重复把同一个场次编号写多次。
7. 本幕场次格式固定为：
   - 当进入新的一节时：{act_label}·第1节 / 第2节 / 第3节
   - 第{start_scene_index}场 / 第{start_scene_index + 1}场 / 第{start_scene_index + 2}场 ...
   - 中文场景标题（内景/外景 + 场所 + 时间）
   - 场景动作与人物对白
8. 这一幕的总字数目标控制在 4000 字左右，建议尽量落在 3500-4500 字之间；必须完整写完本幕，不能中途停下，也不能写到下一幕。
9. 如果素材偏多，优先压缩重复动作描写、解释性台词和抒情铺陈，让这一幕在完整收口的前提下保持克制。
10. 必须直接在场景动作和人物对白里体现承接关系、行动、冲突和明确的新后果；本幕结尾要能看出这一幕已经完成。
11. 禁止复用最近几场的场景标题、核心对白、动作调度和情绪铺陈。
12. 禁止空转、重复解释、只抒情不推进，也不要突然跳去无关支线。
13. 正文里严禁出现“校验备注”“上一场位于”“当前目标”“动作描述”“承接上场”“承接上节”等内部提示词或说明性小标题。

当前幕次目标：
- 当前幕次：{act_label}
- 本幕必须完成的关键节点：{act_target_line}
- 当前节点关键词：{current_target_keywords}
- 下一幕承接点：{next_target or next_act_label or '根据剧情自然衔接'}
- 下一幕关键词：{next_target_keywords}
- 本幕剩余待完成节点数：{remaining_count}

最近几场摘要：
{recent_scene_digest or '- 暂无最近场次摘要'}

这些节点已经写过了，本次禁止再把它们当成核心事件重写：
{completed_digest}

本幕已完成的大纲节点：
{covered_digest}

本幕仍待完成的大纲节点：
{pending_digest}

人物设定：
{characters or '沿用已有正文中的人物关系'}

最早核心设定：
{idea_excerpt}

题设锚点约束：
{idea_guardrails}

上一段关键信息：
- 最近场景：{current_scene}
- 关键对白：{last_dialogue_hint}
- 关键线索：{prop}
- 推进提示：{progression_hint}

已有正文（只供承接，不要重写）：
{cleaned[-2200:]}
"""

    return {
        "prompt": prompt,
        "start_scene_index": start_scene_index,
        "act_label": act_label,
        "section_index": section_index,
        "current_scene": current_scene,
        "current_target": current_target,
        "next_target": next_target,
        "next_act_label": next_act_label,
        "act_pending_items": act_pending_items,
        "outline_progress": outline_progress,
    }


def _build_next_act_text(
    content: str,
    outline: str = "",
    characters: str = "",
    idea: str = "",
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> str:
    return _build_next_act_result(
        content,
        outline=outline,
        characters=characters,
        idea=idea,
        script_format=script_format,
    ).get("text", "")


def _build_next_act_result(
    content: str,
    outline: str = "",
    characters: str = "",
    idea: str = "",
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    prompt_payload = _build_next_act_prompt(content, outline, characters, idea=idea, script_format=script_format)
    prompt = prompt_payload["prompt"]
    start_scene_index = prompt_payload["start_scene_index"]
    act_label = prompt_payload["act_label"]
    current_scene = prompt_payload["current_scene"]
    outline_progress = prompt_payload["outline_progress"]
    fallback_heading = _infer_next_scene_title(current_scene, start_scene_index)

    last_failure_reason = "模型没有返回可用的新一幕内容"
    last_candidate = ""

    for attempt in range(1):
        attempt_prompt = prompt

        try:
            normalized = _generate_complete_act_candidate(
                attempt_prompt,
                act_label=act_label,
                section_index=1,
                start_scene_index=start_scene_index,
                fallback_heading=fallback_heading,
                max_tokens=4200,
            )
        except Exception:
            normalized = ""

        if not normalized:
            last_failure_reason = "模型没有返回可用的新一幕内容"
            continue

        last_candidate = normalized
        validation = _validate_generated_act(
            normalized,
            content,
            outline_progress,
            outline,
            idea=idea,
            characters=characters,
            script_format=script_format,
        )
        if validation.get("ok"):
            return {
                "text": validation.get("cleaned") or normalized,
                "reason": "",
                "validation": _build_generation_review_validation(is_valid=True),
                "accepted_with_issues": False,
            }

        last_failure_reason = validation.get("reason") or "新一幕校验未通过"

    if last_candidate:
        return {
            "text": last_candidate,
            "reason": last_failure_reason or "新一幕需要人工检查",
            "validation": _build_generation_review_validation(
                is_valid=False,
                reason=last_failure_reason or "新一幕需要人工检查",
                corrected=True,
                accepted_with_issues=True,
            ),
            "accepted_with_issues": True,
        }

    return {
        "text": "",
        "reason": last_failure_reason or "模型未能生成通过校验的新一幕",
        "validation": _build_generation_review_validation(
            is_valid=False,
            reason=last_failure_reason or "模型未能生成通过校验的新一幕",
            corrected=True,
            accepted_with_issues=False,
        ),
        "accepted_with_issues": False,
    }


def _generate_next_act(
    content: str,
    outline: str = "",
    characters: str = "",
    idea: str = "",
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> dict[str, Any]:
    merged_content = _strip_internal_scaffolding(content)
    completion = _build_completion_fallback(merged_content, outline, script_format=script_format)
    if completion.get("is_complete") or completion.get("generation_locked") or completion.get("can_continue") is False:
        return {
            "text": "",
            "merged_content": merged_content,
            "completion": completion,
            "is_complete": bool(completion.get("is_complete")),
            "error": "",
            "validation": _build_generation_review_validation(is_valid=True),
            "accepted_with_issues": False,
        }

    act_result = _build_next_act_result(
        merged_content,
        outline=outline,
        characters=characters,
        idea=idea,
        script_format=script_format,
    )
    next_act = _strip_internal_scaffolding(act_result.get("text", ""))
    validation = act_result.get("validation") or _build_generation_review_validation(is_valid=True)
    accepted_with_issues = bool(act_result.get("accepted_with_issues"))

    if next_act:
        merged_content = _strip_internal_scaffolding(f"{merged_content}\n\n{next_act}") if merged_content else next_act
        completion = _build_completion_fallback(merged_content, outline, script_format=script_format)

    return {
        "text": next_act,
        "merged_content": merged_content,
        "completion": completion,
        "is_complete": bool(completion.get("is_complete")),
        "error": act_result.get("reason", "") if not next_act else "",
        "validation": validation,
        "accepted_with_issues": accepted_with_issues,
    }

class ActRequest(BaseModel):
    content: str
    outline: Optional[str] = None
    characters: Optional[str] = None
    idea: Optional[str] = None
    script_format: str = DEFAULT_SCRIPT_FORMAT


class ActReviewRequest(BaseModel):
    content: str
    outline: Optional[str] = None
    characters: Optional[str] = None
    idea: Optional[str] = None
    analysis: Optional[dict[str, Any]] = None
    script_format: str = DEFAULT_SCRIPT_FORMAT


@router.post("/sync_graph")
async def sync_narrative_graph(req: ActRequest):
    data = neo4j_client.sync_graph_from_text(_strip_internal_scaffolding(req.content))
    return {
        "status": "success",
        "graph_id": data.get("graph_id", ""),
        "storage_backend": data.get("storage_backend", "mock"),
        "data": data,
    }


@router.get("/graph_snapshot")
async def query_narrative_graph_snapshot(graph_id: Optional[str] = None):
    data = neo4j_client.get_graph_snapshot(graph_id=graph_id)
    return {
        "status": "success",
        "graph_id": data.get("graph_id", ""),
        "storage_backend": data.get("storage_backend", "mock"),
        "data": data,
    }


@router.post("/review_current_act")
async def review_current_act(req: ActReviewRequest):
    content = _strip_internal_scaffolding(req.content)
    if not content:
        raise HTTPException(status_code=400, detail="当前剧本文本为空，无法分析当前幕")

    script_format = normalize_script_format(req.script_format)
    analysis = _build_current_act_review(
        content,
        outline=req.outline or "",
        idea=req.idea or "",
        characters=req.characters or "",
        script_format=script_format,
    )
    return {"status": "success", "analysis": analysis}


@router.post("/revise_current_act")
async def revise_current_act(req: ActReviewRequest):
    content = _strip_internal_scaffolding(req.content)
    if not content:
        raise HTTPException(status_code=400, detail="当前剧本文本为空，无法修订当前幕")

    script_format = normalize_script_format(req.script_format)
    try:
        result = _revise_current_act(
            content,
            outline=req.outline or "",
            characters=req.characters or "",
            idea=req.idea or "",
            analysis=req.analysis,
            script_format=script_format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"当前幕修订失败：{exc}") from exc

    return {
        "status": "success",
        "act_label": result.get("act_label", ""),
        "analysis": result.get("analysis", {}),
        "revised_act": result.get("revised_act", ""),
        "revised_content": result.get("revised_content", ""),
        "completion": result.get("completion", {}),
        "accepted_with_issues": bool(result.get("accepted_with_issues")),
        "warning": result.get("warning", ""),
        "generated": bool(result.get("generated")),
    }


@router.post("/generate_act")
async def generate_next_act(req: ActRequest):
    content = _strip_internal_scaffolding(req.content)
    if not content:
        raise HTTPException(status_code=400, detail="当前剧本文本为空，无法生成下一幕")

    script_format = normalize_script_format(req.script_format)
    generation = _generate_next_act(
        content,
        outline=req.outline or "",
        characters=req.characters or "",
        idea=req.idea or "",
        script_format=script_format,
    )
    next_act = generation.get("text", "")
    if not next_act:
        completion = generation.get("completion") or _build_completion_fallback(
            content,
            req.outline or "",
            script_format=script_format,
        )
        if completion.get("generation_locked") or completion.get("can_continue") is False:
            graph_data = neo4j_client.sync_graph_from_text(content)
            return {
                "status": "success",
                "text": "",
                "data": graph_data,
                "completion": completion,
                "is_complete": bool(completion.get("is_complete")),
                "generation_locked": bool(completion.get("generation_locked")),
                "validation": generation.get("validation") or _build_generation_review_validation(is_valid=True),
                "accepted_with_issues": bool(generation.get("accepted_with_issues")),
            }
        raise HTTPException(
            status_code=502,
            detail=generation.get("error") or "下一幕生成失败：模型未返回通过校验的新正文",
        )
    merged = generation.get("merged_content") or content
    graph_data = neo4j_client.sync_graph_from_text(merged)
    completion = generation.get("completion") or _build_completion_fallback(
        merged,
        req.outline or "",
        script_format=script_format,
    )

    return {
        "status": "success",
        "text": next_act,
        "data": graph_data,
        "completion": completion,
        "is_complete": bool(completion.get("is_complete")),
        "generation_locked": bool(completion.get("generation_locked")),
        "validation": generation.get("validation") or _build_generation_review_validation(is_valid=True),
        "accepted_with_issues": bool(generation.get("accepted_with_issues")),
    }
