import json
import re
from typing import Any, Optional

import openai
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.rule_engine import NarrativeRuleEngine
from app.core.runtime_ai_settings import (
    PROVIDER_OPTIONS,
    ensure_runtime_settings_file,
    get_effective_generation_settings,
    load_runtime_settings,
    save_runtime_settings,
)
from app.core.script_formats import (
    DEFAULT_SCRIPT_FORMAT,
    build_all_act_label_pattern,
    get_act_sequence,
    get_outline_sections,
    get_script_format_label,
    normalize_script_format,
)
from app.core.story_constraints import build_story_guardrail_block

router = APIRouter()
rule_engine = NarrativeRuleEngine()


class RuntimeSettingsUpdateRequest(BaseModel):
    model_base: Optional[str] = None
    zhipu_model: Optional[str] = None
    openai_model: Optional[str] = None
    deepseek_model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    safety_provider: Optional[str] = None
    zhipu_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None


class CharacterRequest(BaseModel):
    idea: str = Field(min_length=1)
    script_format: str = DEFAULT_SCRIPT_FORMAT


class OutlineRequest(BaseModel):
    idea: str = Field(min_length=1)
    characters: str = ""
    script_format: str = DEFAULT_SCRIPT_FORMAT


class PipelineScriptRequest(BaseModel):
    idea: str = Field(min_length=1)
    characters: str = ""
    outline: str = ""
    script_format: str = DEFAULT_SCRIPT_FORMAT


class NextSeriesEpisodePrefillRequest(BaseModel):
    current_episode: str = Field(min_length=1)
    script_format: str = "series"


SERIES_NEXT_EPISODE_FIELD_SPECS = [
    {
        "key": "previous_ending",
        "label": "上一集结尾剧情",
        "description": "只概括上一集临近结尾、对下一集最关键的剧情状态、悬念和未解决问题，不要把整集正文原样搬进来。",
    },
    {
        "key": "character_focus",
        "label": "本集人物重心",
        "description": "为下一集提炼最适合作为主推进的人物焦点，写清下集最值得跟进的人物、核心困境和关键选择。",
    },
    {
        "key": "tone_direction",
        "label": "本集调性与走向",
        "description": "概括下一集应延续或升级的情绪基调、冲突走向和叙事节奏。",
    },
    {
        "key": "cliffhanger",
        "label": "本集结尾悬念",
        "description": "写下一集结束时最适合留下的悬念、反转或钩子。这一项写的是下一集的结尾悬念，不是当前集结尾的重复复述。",
    },
]


SAFETY_PATTERNS = {
    "tencent": [
        "制作炸弹",
        "枪支改造",
        "黑客入侵",
        "窃取账号",
        "毒品配方",
        "自杀教程",
        "恐怖袭击",
    ],
    "basic": [
        "制作炸弹",
        "枪支改造",
        "黑客入侵",
        "自杀教程",
    ],
}

MODEL_CONNECT_TIMEOUT_SECONDS = 30
MODEL_READ_TIMEOUT_SECONDS = 600


def clean_text_output(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"`{3,}.*?`{3,}", "", text, flags=re.DOTALL)
    text = re.sub(r"^[ \t>*#-]+", "", text, flags=re.MULTILINE)
    text = text.replace("EXT.", "外景")
    text = text.replace("INT.", "内景")
    text = text.replace("(O.S.)", "画外音")
    text = text.replace("O.S.", "画外音")
    text = re.sub(r"[*#`_]+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = clean_text_output(text)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("模型没有返回 JSON 对象")

    return json.loads(match.group(0))


def looks_garbled(text: str) -> bool:
    if not text:
        return True

    chinese_hits = len(re.findall(r"[\u4e00-\u9fff]", text))
    weird_hits = len(re.findall(r"[ÃÂÐÎÒÙÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]", text))
    return weird_hits >= 3 or chinese_hits < max(30, len(text) // 14)


def run_safety_review(prompt: str, safety_provider: str) -> None:
    if safety_provider == "off":
        return

    blocked_terms = SAFETY_PATTERNS.get(safety_provider, SAFETY_PATTERNS["basic"])
    hits = [term for term in blocked_terms if term in prompt]
    if hits:
        raise HTTPException(
            status_code=400,
            detail=f"内容未通过安全审核，当前策略已拦截敏感指令：{hits[0]}",
        )

def _extract_message_content(choice: Any) -> str:
    message = choice.get("message", {}) if isinstance(choice, dict) else getattr(choice, "message", None)
    if isinstance(message, dict):
        return message.get("content") or ""
    return getattr(message, "content", "") or ""


def _extract_finish_reason(choice: Any) -> str:
    if isinstance(choice, dict):
        return str(choice.get("finish_reason") or "")
    return str(getattr(choice, "finish_reason", "") or "")


def _normalize_usage_payload(usage: Any) -> dict[str, Any]:
    if not usage:
        return {}
    if isinstance(usage, dict):
        return usage

    payload: dict[str, Any] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = getattr(usage, key, None)
        if value is not None:
            payload[key] = value

    details = getattr(usage, "prompt_tokens_details", None)
    if isinstance(details, dict):
        payload["prompt_tokens_details"] = details
    elif details is not None and hasattr(details, "__dict__"):
        payload["prompt_tokens_details"] = {
            key: value for key, value in vars(details).items() if value is not None
        }

    return payload


def call_model_with_meta(prompt: str, effective: dict[str, Any], max_tokens: int) -> tuple[str, dict[str, Any]]:
    provider = effective["provider"]
    model = effective["model"]
    temperature = effective["temperature"]
    top_p = effective["top_p"]
    api_key = effective["api_key"]

    if not api_key:
        raise HTTPException(status_code=400, detail=f"{effective['provider_label']} API Key 未配置")

    if provider == "openai":
        openai.api_key = api_key
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        return _extract_message_content(choice), {
            "finish_reason": _extract_finish_reason(choice),
            "usage": _normalize_usage_payload(getattr(response, "usage", None)),
        }

    if provider == "zhipu":
        from zhipuai import ZhipuAI

        client = ZhipuAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        return _extract_message_content(choice), {
            "finish_reason": _extract_finish_reason(choice),
            "usage": _normalize_usage_payload(getattr(response, "usage", None)),
        }

    if provider == "deepseek":
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens,
                },
                timeout=(MODEL_CONNECT_TIMEOUT_SECONDS, MODEL_READ_TIMEOUT_SECONDS),
            )
        except requests.Timeout as exc:
            raise HTTPException(
                status_code=504,
                detail=(
                    f"DeepSeek 响应超时（>{MODEL_READ_TIMEOUT_SECONDS} 秒），"
                    "请稍后重试，或缩短要求后重新生成。"
                ),
            ) from exc
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"DeepSeek 请求失败：{exc}") from exc

        if not response.ok:
            detail = ""
            try:
                payload = response.json()
                detail = (
                    payload.get("error", {}).get("message")
                    or payload.get("message")
                    or payload.get("detail")
                    or ""
                )
            except ValueError:
                detail = response.text.strip()
            raise HTTPException(
                status_code=response.status_code,
                detail=f"DeepSeek 返回错误：{detail or response.reason}",
            )

        payload = response.json()
        choice = (payload.get("choices") or [{}])[0]
        return _extract_message_content(choice), {
            "finish_reason": _extract_finish_reason(choice),
            "usage": _normalize_usage_payload(payload.get("usage")),
        }

    raise HTTPException(status_code=400, detail="不支持的模型提供商")

def call_model(prompt: str, effective: dict[str, Any], max_tokens: int) -> str:
    raw, _ = call_model_with_meta(prompt, effective, max_tokens=max_tokens)
    return raw


def generate_clean_content_with_meta(
    prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: int = 2000,
):
    effective = get_effective_generation_settings(
        {
            "model": model,
            "temperature": temperature,
            "top_p": top_p,
        }
    )
    run_safety_review(prompt, effective["safety_provider"])
    raw, response_meta = call_model_with_meta(prompt, effective, max_tokens=max_tokens)
    text = clean_text_output(raw)
    if looks_garbled(text):
        raise ValueError("模型返回内容疑似乱码")
    return text, effective, response_meta


def generate_clean_content(
    prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: int = 2000,
):
    text, effective, _ = generate_clean_content_with_meta(
        prompt,
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )
    return text, effective


def _normalize_stage_content(content: str, stage: str) -> str:
    if stage == "script":
        return enforce_script_labels(content)
    return clean_text_output(content)


def _generate_stage_content_with_retries(
    *,
    prompt: str,
    stage: str,
    idea: str,
    characters: str = "",
    script_format: str = DEFAULT_SCRIPT_FORMAT,
    max_tokens: int,
    initial_content: Optional[str] = None,
) -> tuple[str, dict[str, Any], dict[str, Any], bool, bool, bool]:
    effective = get_effective_generation_settings()
    corrected = False
    last_prepared = ""
    last_validation: Optional[dict[str, Any]] = None

    if initial_content:
        prepared = _normalize_stage_content(initial_content, stage)
        validation = rule_engine.evaluate(
            prepared,
            stage=stage,
            idea=idea,
            characters=characters,
            script_format=script_format,
        )
        last_prepared = prepared
        last_validation = validation
        if validation["is_valid"]:
            return prepared, effective, validation, corrected, True, False
        corrected = True
        last_errors = validation["hard_errors"]
    else:
        last_errors = []

    last_note = ""
    for attempt in range(3):
        attempt_prompt = prompt if attempt == 0 else build_correction_prompt(prompt, last_errors)
        content, effective = generate_clean_content(attempt_prompt, max_tokens=max_tokens)
        prepared = _normalize_stage_content(content, stage)
        validation = rule_engine.evaluate(
            prepared,
            stage=stage,
            idea=idea,
            characters=characters,
            script_format=script_format,
        )
        last_prepared = prepared
        last_validation = validation
        if validation["is_valid"]:
            return prepared, effective, validation, corrected or attempt > 0, False, False
        corrected = True
        last_errors = validation["hard_errors"]
        last_note = "；".join(item.get("description", "") for item in last_errors[:3] if item.get("description"))

    if stage == "script" and last_prepared and last_validation:
        return last_prepared, effective, last_validation, corrected, False, True

    raise ValueError(last_note or f"{stage} generation failed rule validation")


ACT_LABEL_PATTERN = build_all_act_label_pattern()
SECTION_LABEL_RE = re.compile(rf"^{ACT_LABEL_PATTERN}[·.、 ]?第([一二三四五六七八九十百零\d]+)节$")
SCENE_LABEL_RE = re.compile(r"^第([一二三四五六七八九十百零\d]+)场$")


def _normalize_act_label(label: str) -> str:
    return str(label or "").strip()


def _number_text_to_int(raw: str) -> int:
    text = str(raw or "").strip()
    if not text:
        return 0
    if text.isdigit():
        return int(text)

    digit_map = {
        "零": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    if text == "十":
        return 10
    if "十" in text:
        prefix, suffix = text.split("十", 1)
        tens = digit_map.get(prefix, 1 if prefix == "" else 0)
        ones = digit_map.get(suffix, 0) if suffix else 0
        return tens * 10 + ones
    return digit_map.get(text, 0)


def _fallback_act_section_by_scene_index(index: int) -> tuple[str, int]:
    act_sequence = get_act_sequence(DEFAULT_SCRIPT_FORMAT)
    if index <= 4:
        return act_sequence[0], 1
    if index <= 8:
        return act_sequence[min(1, len(act_sequence) - 1)], 1
    return act_sequence[-1], 1


def _split_inline_script_headers(text: str) -> str:
    normalized = clean_text_output(text)
    if not normalized:
        return ""

    normalized = re.sub(
        rf"(?P<section>{ACT_LABEL_PATTERN}[·.、 ]?第[一二三四五六七八九十百零\d]+节)\s*(?P<scene>第[一二三四五六七八九十百零\d]+场)",
        lambda match: f"{match.group('section')}\n{match.group('scene')}",
        normalized,
    )
    normalized = re.sub(
        r"(第[一二三四五六七八九十百零\d]+场)\s*((?:内景|外景)\s+.+)",
        r"\1\n\2",
        normalized,
    )
    return clean_text_output(normalized)


def enforce_script_labels(
    text: str,
    *,
    default_act_label: str | None = None,
    start_scene_index: int = 1,
    max_sections: int = 3,
    single_act: bool = False,
) -> str:
    cleaned = _split_inline_script_headers(text)
    if not cleaned:
        return cleaned

    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
    if not any(line.startswith(("内景", "外景")) for line in lines):
        return cleaned

    raw_blocks: list[dict[str, Any]] = []
    pending_act_label = ""
    pending_section_no: int | None = None
    current_act_label = _normalize_act_label(default_act_label or "") if single_act else ""
    current_section_no = 1
    active_block: dict[str, Any] | None = None

    for line in lines:
        section_match = SECTION_LABEL_RE.match(line)
        if section_match:
            pending_act_label = _normalize_act_label(section_match.group(1))
            pending_section_no = max(1, _number_text_to_int(section_match.group(2)) or 1)
            current_act_label = pending_act_label or current_act_label
            current_section_no = pending_section_no or current_section_no
            continue

        if SCENE_LABEL_RE.match(line):
            continue

        if line.startswith(("内景", "外景")):
            if active_block:
                raw_blocks.append(active_block)
            active_block = {
                "act_label": pending_act_label or current_act_label,
                "section_no": pending_section_no or current_section_no,
                "scene_heading": line,
                "body": [],
            }
            if pending_act_label:
                current_act_label = pending_act_label
            if pending_section_no:
                current_section_no = pending_section_no
            pending_act_label = ""
            pending_section_no = None
            continue

        if active_block:
            active_block["body"].append(line)

    if active_block:
        raw_blocks.append(active_block)

    if not raw_blocks:
        return cleaned

    resolved_default_label = _normalize_act_label(default_act_label or "")
    resolved_blocks: list[dict[str, Any]] = []
    scene_index = max(1, int(start_scene_index or 1))
    last_act_label = resolved_default_label if single_act else ""
    last_section_no = 1

    for block in raw_blocks:
        act_label = _normalize_act_label(block.get("act_label") or "")
        section_no = int(block.get("section_no") or 0)

        if single_act and resolved_default_label:
            act_label = resolved_default_label
        elif not act_label:
            act_label = last_act_label

        if not act_label:
            act_label, fallback_section = _fallback_act_section_by_scene_index(scene_index)
            if not section_no:
                section_no = fallback_section

        if not section_no:
            section_no = last_section_no or 1

        resolved_blocks.append(
            {
                "act_label": act_label,
                "section_no": max(1, section_no),
                "scene_heading": block["scene_heading"],
                "body": block["body"],
            }
        )
        last_act_label = act_label
        last_section_no = max(1, section_no)
        scene_index += 1

    section_mapping: dict[int, int] = {}
    next_section_no = 1
    for block in resolved_blocks:
        raw_section_no = int(block["section_no"])
        if raw_section_no not in section_mapping:
            section_mapping[raw_section_no] = min(next_section_no, max(1, int(max_sections or 3)))
            next_section_no += 1
        block["section_no"] = section_mapping[raw_section_no]

    rebuilt: list[str] = []
    last_section_key: tuple[str, int] | None = None
    scene_index = max(1, int(start_scene_index or 1))

    for block in resolved_blocks:
        section_key = (block["act_label"], int(block["section_no"]))
        if section_key != last_section_key:
            rebuilt.append(f"{block['act_label']}·第{block['section_no']}节")
            last_section_key = section_key

        rebuilt.append(f"第{scene_index}场")
        rebuilt.append(block["scene_heading"])
        rebuilt.extend(block["body"])
        rebuilt.append("")
        scene_index += 1

    return clean_text_output("\n".join(rebuilt))


def build_meta(effective: dict[str, Any], mode: str, stage: str, note: Optional[str] = None):
    meta = {
        "stage": stage,
        "mode": mode,
        "provider": effective["provider"],
        "provider_label": effective["provider_label"],
        "model": effective["model"],
        "temperature": effective["temperature"],
        "top_p": effective["top_p"],
        "safety_provider": effective["safety_provider"],
        "safety_label": effective["safety_label"],
        "provider_ready": effective["provider_ready"],
    }
    if note:
        meta["note"] = note
    return meta


def attach_rule_validation(
    meta: dict[str, Any],
    validation: dict[str, Any],
    corrected: bool = False,
    accepted_with_issues: bool = False,
):
    meta["rule_validation"] = {
        "is_valid": validation["is_valid"],
        "hard_errors": validation["hard_errors"],
        "soft_warnings": validation["soft_warnings"],
        "metrics": validation["metrics"],
        "corrected": corrected,
        "accepted_with_issues": accepted_with_issues,
    }
    return meta


def build_correction_prompt(base_prompt: str, hard_errors: list[dict[str, str]]) -> str:
    fix_lines = [f"- {item.get('fix_instruction', '')}" for item in hard_errors if item.get("fix_instruction")]
    if not fix_lines:
        return base_prompt

    return (
        f"{base_prompt}\n\n"
        "上一个版本未通过校验。请优先修复题设锚点缺失，再修复结构问题。以下要求必须全部满足：\n"
        f"{'\n'.join(fix_lines)}\n"
        "只输出修正后的最终中文结果，不要解释过程。"
    )


def build_characters_prompt(idea: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> str:
    resolved_format = normalize_script_format(script_format)
    format_label = get_script_format_label(resolved_format)
    guardrails = build_story_guardrail_block(idea, "characters")
    return f"""你是一名严谨的中文影视编剧策划。你的第一职责是保留用户题设，不得擅自替换职业、人物关系、地点、线索和任务。

{guardrails}

请根据下面的核心设定，输出纯中文的人物设定。

要求：
1. 只输出中文，不要使用 Markdown，不要出现星号、井号、代码块。
2. 不要写英文场景标记，不要写多余说明。
3. 内容包括：主角、对手人物、协助人物、关键关系、每个人的目标与矛盾。
4. 主角身份必须与题设一致；若题设出现亲属关系、求救信号、实验站等信息，人物关系中必须明确承接。
5. 每个人物都要写清：姓名、身份、目标、矛盾、与主线的连接方式。
6. 当前剧本形式题材是“{format_label}”，请让人物配置天然适合这一题材的篇幅和推进方式。
7. 语气专业、清晰，便于后续继续生成剧情。

核心设定：
{idea}
"""


def build_outline_prompt(idea: str, characters: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> str:
    resolved_format = normalize_script_format(script_format)
    format_label = get_script_format_label(resolved_format)
    outline_sections = get_outline_sections(resolved_format)
    structure_lines = "\n".join(f"{index + 1}. {label}：{description}" for index, (label, description) in enumerate(outline_sections))
    act_labels = "、".join(label for label, _ in outline_sections)
    guardrails = build_story_guardrail_block(idea, "outline")
    return f"""你是一名严谨的中文影视编剧。你必须先保留用户题设，再进行扩写，不允许另起炉灶写成别的故事。

{guardrails}

请根据核心设定和人物设定，输出纯中文剧情大纲。当前剧本形式题材是“{format_label}”。

要求：
1. 只输出中文，不要使用 Markdown，不要出现星号、井号、代码块。
2. 大纲必须连续写出这些幕次：{act_labels}。
3. 每一幕都要突出主要矛盾的升级，并严格对应以下结构：
{structure_lines}
4. 大纲中必须明确落地题设中的主角身份、关键场域和核心任务，不能把它们替换成别的设定。
5. 文风简洁、准确、具有电影感。
6. 每一幕都最多只写 3 个推进点，每个推进点只用 1 句话讲清楚，不要把 6 到 8 句事件堆在同一幕里。
7. 这个大纲后续要按“每次完整生成一幕”的方式执行，所以每一幕都必须控制在 1 到 3 个关键推进点内，便于后端一次性把这一幕完整写完。

核心设定：
{idea}

人物设定：
{characters}
"""


def clean_screenplay_title(raw: str) -> str:
    title = clean_text_output(raw)
    title = re.sub(r"^(剧名|片名|名称|标题)\s*[:：]\s*", "", title)
    title = title.splitlines()[0] if title else ""
    title = re.split(r"[，,。；;：:\s]+", title)[0].strip()
    title = title.strip("《》「」『』“”\"'`*#")
    title = re.sub(r"[\\/:*?\"<>|]", "", title)
    title = re.sub(r"\s+", "", title)
    return title[:12]


def derive_fallback_title(idea: str, outline: str) -> str:
    source = clean_text_output(outline or idea)
    candidates = re.findall(r"[\u4e00-\u9fff]{2,8}", source)
    ignored = {"第一幕", "第二幕", "第三幕", "第四幕", "第五幕", "第六幕", "剧情大纲", "核心设定"}
    for candidate in candidates:
        if candidate not in ignored and not candidate.endswith(("阶段", "结构", "故事", "人物")):
            return candidate[:8]
    return "未命名剧本"


def build_title_prompt(idea: str, characters: str, outline: str, script_format: str = DEFAULT_SCRIPT_FORMAT) -> str:
    format_label = get_script_format_label(normalize_script_format(script_format))
    return f"""你是中文影视剧名策划。请根据当前剧本的大纲、人物和核心设定，为这个“{format_label}”生成一个正式剧名。

要求：
1. 只输出一个剧名，不要解释，不要加书名号。
2. 剧名必须贴合当前故事内容，不能使用通用占位名。
3. 尽量控制在 2 到 8 个汉字，可以有意象感，但不能空泛。
4. 不要包含“剧本”“故事”“第一幕”等说明词。

核心设定：
{idea}

人物设定：
{characters}

剧情大纲：
{outline}
"""


def generate_screenplay_title(
    *,
    idea: str,
    characters: str,
    outline: str,
    script_format: str = DEFAULT_SCRIPT_FORMAT,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    prompt = build_title_prompt(idea, characters, outline, script_format)
    effective = get_effective_generation_settings({"temperature": 0.72, "top_p": 0.9})
    run_safety_review(prompt, effective["safety_provider"])
    raw, response_meta = call_model_with_meta(prompt, effective, max_tokens=80)
    title = clean_screenplay_title(raw)
    return title or derive_fallback_title(idea, outline), effective, response_meta


def build_series_next_episode_prefill_prompt(current_episode: str) -> str:
    field_lines = "\n".join(
        f"{index + 1}. {item['key']} / {item['label']}：{item['description']}"
        for index, item in enumerate(SERIES_NEXT_EPISODE_FIELD_SPECS)
    )
    return f"""你是一名中文电视剧分集策划助理。你的任务不是总结全文，而是根据“当前这一集已经生成好的完整正文”，为“下一集自动化工坊”里的 4 个输入框分别生成预填内容。

请严格按照下面每个输入框的填写目标来写，不能把整集正文原样搬进去，也不能把四个字段写成同一种内容：
{field_lines}

规则：
1. 只输出 JSON，不要输出解释、前后缀或 Markdown。
2. 必须保留当前集已经形成的角色关系、主线任务、冲突方向和悬念来源，不要脱离现有正文另起炉灶。
3. previous_ending 只写“上一集结尾对下一集最关键的承接信息”，控制在 2 到 4 句。
4. character_focus 要写“下一集最值得跟进的人物重心”，不能只是重复上一集发生了什么，控制在 2 到 4 句。
5. tone_direction 要写“下一集的调性与走向”，控制在 1 到 3 句。
6. cliffhanger 要写“下一集结束时应该留下什么悬念”，控制在 1 到 3 句，不能直接重复当前集已经出现过的结尾句子。
7. 所有字段都必须返回非空字符串。

输出格式：
{{
  "previous_ending": "上一集结尾剧情",
  "character_focus": "本集人物重心",
  "tone_direction": "本集调性与走向",
  "cliffhanger": "本集结尾悬念"
}}

当前这一集的完整正文：
{current_episode}
"""


def generate_series_next_episode_prefill(current_episode: str) -> tuple[dict[str, str], dict[str, Any]]:
    prompt = build_series_next_episode_prefill_prompt(current_episode)
    raw, effective = generate_clean_content(prompt, temperature=0.35, max_tokens=1400)
    payload = _extract_json_object(raw)

    result: dict[str, str] = {}
    for field in SERIES_NEXT_EPISODE_FIELD_SPECS:
        key = field["key"]
        compact_key = key.replace("_", "")
        camel_key = "".join(
            part if index == 0 else part[:1].upper() + part[1:]
            for index, part in enumerate(key.split("_"))
        )
        value = clean_text_output(
            str(
                payload.get(key)
                or payload.get(compact_key)
                or payload.get(camel_key)
                or ""
            )
        )
        if not value:
            raise ValueError(f"字段 {key} 为空")
        result[key] = value

    return result, effective


@router.get("/runtime-settings")
def get_runtime_settings():
    ensure_runtime_settings_file()
    return load_runtime_settings(include_secrets=False)


@router.post("/runtime-settings")
def update_runtime_settings(request: RuntimeSettingsUpdateRequest):
    return save_runtime_settings(request.model_dump(exclude_none=True))


@router.post("/narrative/characters")
def generate_characters_api(req: CharacterRequest):
    script_format = normalize_script_format(req.script_format)
    prompt = build_characters_prompt(req.idea, script_format)
    try:
        content, effective, validation, corrected, _, accepted_with_issues = _generate_stage_content_with_retries(
            prompt=prompt,
            stage="characters",
            idea=req.idea,
            script_format=script_format,
            max_tokens=2200,
        )

        meta = build_meta(effective, "model", "characters")
        attach_rule_validation(meta, validation, corrected=corrected, accepted_with_issues=accepted_with_issues)
        return {"characters": content, "meta": meta}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"人物设定生成失败：{exc}")


@router.post("/narrative/outline")
def generate_outline_api(req: OutlineRequest):
    script_format = normalize_script_format(req.script_format)
    prompt = build_outline_prompt(req.idea, req.characters, script_format)
    try:
        content, effective, validation, corrected, _, accepted_with_issues = _generate_stage_content_with_retries(
            prompt=prompt,
            stage="outline",
            idea=req.idea,
            characters=req.characters,
            script_format=script_format,
            max_tokens=2600,
        )

        meta = build_meta(effective, "model", "outline")
        attach_rule_validation(meta, validation, corrected=corrected, accepted_with_issues=accepted_with_issues)
        try:
            title, title_effective, title_response_meta = generate_screenplay_title(
                idea=req.idea,
                characters=req.characters,
                outline=content,
                script_format=script_format,
            )
            meta["generated_title"] = title
            meta["title_model"] = build_meta(title_effective, "model", "title")
            meta["title_model"]["response"] = title_response_meta
        except Exception:
            title = derive_fallback_title(req.idea, content)
            meta["generated_title"] = title
            meta["title_model"] = {"fallback": True}
        return {"outline": content, "title": title, "meta": meta}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"剧情大纲生成失败：{exc}")


@router.post("/narrative/script")
def generate_pipeline_script_api(req: PipelineScriptRequest):
    try:
        from app.api import narrative as narrative_api

        script_format = normalize_script_format(req.script_format)
        generation = narrative_api._generate_next_act(
            "",
            outline=req.outline or "",
            characters=req.characters or "",
            idea=req.idea or "",
            script_format=script_format,
        )
        content = narrative_api._strip_internal_scaffolding(generation.get("text", ""))
        if not content:
            raise ValueError(generation.get("error") or "第一幕生成失败：模型未返回通过校验的正文")

        effective = get_effective_generation_settings()
        validation = generation.get("validation") or rule_engine.evaluate(
            content,
            stage="script",
            idea=req.idea,
            characters=req.characters,
            script_format=script_format,
        )
        accepted_with_issues = bool(generation.get("accepted_with_issues"))
        completion = generation.get("completion") or narrative_api._build_completion_fallback(
            content,
            req.outline or "",
            script_format=script_format,
        )

        meta = build_meta(effective, "model", "script")
        meta["generation_mode"] = "first_act_generation"
        meta["generated_scene_count"] = narrative_api._extract_scene_count(content)
        attach_rule_validation(
            meta,
            validation,
            corrected=accepted_with_issues,
            accepted_with_issues=accepted_with_issues,
        )
        if generation.get("error"):
            meta["rule_validation"]["soft_warnings"] = [
                *meta["rule_validation"].get("soft_warnings", []),
                {"description": generation["error"]},
            ]
        return {
            "script": content,
            "meta": meta,
            "completion": completion,
            "is_end": bool(completion.get("is_complete")) if completion else False,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"剧本第一幕生成失败：{exc}")
@router.post("/narrative/series-next-episode-prefill")
def generate_series_next_episode_prefill_api(req: NextSeriesEpisodePrefillRequest):
    script_format = normalize_script_format(req.script_format)
    if script_format != "series":
        raise HTTPException(status_code=400, detail="该接口当前仅支持电视剧/连续剧模式")

    current_episode = clean_text_output(req.current_episode)
    if not current_episode:
        raise HTTPException(status_code=400, detail="当前集正文不能为空")

    try:
        fields, effective = generate_series_next_episode_prefill(current_episode)
        meta = build_meta(effective, "model", "series_next_episode_prefill")
        return {
            "script_format": script_format,
            "fields": fields,
            "meta": meta,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"下一集自动预填生成失败：{exc}")
