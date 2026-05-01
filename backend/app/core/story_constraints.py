import re
from typing import Any


ROLE_SUFFIXES = [
    "工程师",
    "警察",
    "记者",
    "医生",
    "侦探",
    "学生",
    "科学家",
    "研究员",
    "程序员",
    "设计师",
    "律师",
    "教师",
    "船长",
    "飞行员",
    "士兵",
    "特工",
    "演员",
    "作家",
    "教授",
    "学者",
    "站长",
    "队长",
    "护士",
    "摄影师",
    "主播",
    "博主",
    "商人",
    "老板",
    "主管",
    "职员",
    "机器人",
]

SETTING_SUFFIXES = [
    "城市",
    "小镇",
    "海港",
    "港口",
    "实验站",
    "实验室",
    "研究所",
    "基地",
    "空间站",
    "码头",
    "医院",
    "学校",
    "公寓",
    "岛",
    "列车",
    "酒店",
    "工厂",
    "监狱",
    "飞船",
    "庄园",
    "剧院",
    "矿井",
    "车站",
    "港",
    "站",
]

RELATION_TERMS = [
    "失踪哥哥",
    "失踪姐姐",
    "失踪弟弟",
    "失踪妹妹",
    "失踪父亲",
    "失踪母亲",
    "失踪搭档",
    "失踪恋人",
    "失踪朋友",
    "失踪同事",
    "失踪导师",
    "哥哥",
    "姐姐",
    "弟弟",
    "妹妹",
    "父亲",
    "母亲",
    "搭档",
    "恋人",
    "朋友",
    "同事",
    "导师",
    "女儿",
    "儿子",
]

CLUE_TERMS = [
    "求救信号",
    "求救",
    "事故真相",
    "真相",
    "事故",
    "日志",
    "芯片",
    "录音",
    "照片",
    "旧照片",
    "坐标",
    "钥匙",
    "密码",
    "档案",
    "证据",
    "录像",
    "信号",
    "门禁卡",
]

MISSION_VERBS = [
    "潜入",
    "调查",
    "寻找",
    "追查",
    "守住",
    "揭开",
    "阻止",
    "逃离",
    "拯救",
    "回收",
    "修复",
    "保护",
    "破解",
    "夺回",
    "追踪",
]

NOISY_PREFIXES = [
    "一名",
    "一位",
    "一个",
    "某个",
    "某位",
    "近未来",
    "未来",
    "封闭",
    "废弃",
    "神秘",
    "失踪",
    "女",
    "男",
    "年轻",
    "年迈",
    "退役",
    "前",
    "现任",
]

GROUP_STAGE_MAP = {
    "主角身份": {"characters", "outline", "script"},
    "关键场域": {"characters", "outline", "script"},
    "核心关系": {"characters", "outline", "script"},
    "关键线索": {"characters", "outline", "script"},
    "核心任务": {"characters", "outline", "script"},
}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _clean_phrase(raw: str) -> str:
    text = (raw or "").strip()
    text = re.sub(r"^(一名|一位|一个|某个|某位|身为|作为)", "", text)
    text = re.sub(r"[，。！？；：、,.!?;:\s]+$", "", text)
    return text.strip()


def _collect_pattern_matches(text: str, patterns: list[str], limit: int = 3) -> list[str]:
    matches: list[str] = []
    for pattern in patterns:
        for raw_match in re.findall(pattern, text):
            if isinstance(raw_match, tuple):
                candidate = next((part for part in raw_match if part), "")
            else:
                candidate = raw_match
            candidate = _clean_phrase(candidate)
            if candidate and candidate not in matches:
                matches.append(candidate)
            if len(matches) >= limit:
                return matches
    return matches


def _expand_term(term: str) -> list[str]:
    cleaned = _clean_phrase(term)
    variants = [cleaned]

    for prefix in NOISY_PREFIXES:
        if cleaned.startswith(prefix) and len(cleaned) > len(prefix) + 1:
            variants.append(cleaned[len(prefix) :])

    for suffix in ROLE_SUFFIXES + SETTING_SUFFIXES + CLUE_TERMS + RELATION_TERMS:
        if suffix in cleaned:
            variants.append(suffix)

    for verb in MISSION_VERBS:
        if cleaned.startswith(verb) and len(cleaned) > len(verb) + 1:
            variants.append(cleaned[len(verb) :])

    if "事故真相" in cleaned:
        variants.extend(["事故真相", "事故", "真相"])
    if "求救信号" in cleaned:
        variants.extend(["求救信号", "信号"])
    if "海港城市" in cleaned:
        variants.extend(["海港城市", "海港"])

    return _dedupe([item for item in variants if len(item) >= 2])


def _build_group(label: str, terms: list[str]) -> dict[str, Any]:
    deduped_terms = _dedupe([_clean_phrase(term) for term in terms if _clean_phrase(term)])
    variants: list[str] = []
    for term in deduped_terms:
        variants.extend(_expand_term(term))
    return {
        "label": label,
        "primary": deduped_terms[0] if deduped_terms else "",
        "terms": deduped_terms,
        "variants": _dedupe(variants),
        "stages": GROUP_STAGE_MAP[label],
    }


def extract_story_anchor_groups(idea: str) -> list[dict[str, Any]]:
    cleaned = (idea or "").strip()
    if not cleaned:
        return []

    role_pattern = "|".join(re.escape(suffix) for suffix in ROLE_SUFFIXES)
    setting_pattern = "|".join(re.escape(suffix) for suffix in SETTING_SUFFIXES)
    relation_pattern = "|".join(re.escape(term) for term in RELATION_TERMS)

    protagonist_matches = _collect_pattern_matches(
        cleaned,
        [
            rf"(?:一名|一位|一个|某位|某个)?((?:男|女|年轻|年迈|失意|退役|天才|神秘|前|现任)?[\u4e00-\u9fff]{{0,8}}(?:{role_pattern}))",
            rf"((?:男|女)[\u4e00-\u9fff]{{0,6}}(?:{role_pattern}))",
        ],
        limit=2,
    )
    setting_matches = _collect_pattern_matches(
        cleaned,
        [
            rf"((?:近未来|未来|末日|海港|封闭|废弃|地下|边境|偏远|赛博|蒸汽朋克|近海|海上)?[\u4e00-\u9fff]{{0,8}}(?:{setting_pattern}))",
        ],
        limit=3,
    )
    relation_matches = _collect_pattern_matches(
        cleaned,
        [
            rf"((?:神秘)?(?:失踪|受困|逃亡|已故|留下)?(?:{relation_pattern}))",
        ],
        limit=2,
    )

    clue_matches: list[str] = []
    for term in CLUE_TERMS:
        if term in cleaned and term not in clue_matches:
            clue_matches.append(term)
        if len(clue_matches) >= 3:
            break

    mission_matches = _collect_pattern_matches(
        cleaned,
        [rf"((?:{'|'.join(MISSION_VERBS)})[\u4e00-\u9fff]{{2,10}})"],
        limit=3,
    )

    groups: list[dict[str, Any]] = []
    if protagonist_matches:
        groups.append(_build_group("主角身份", protagonist_matches[:1]))
    if setting_matches:
        groups.append(_build_group("关键场域", setting_matches[:2]))
    if relation_matches:
        groups.append(_build_group("核心关系", relation_matches[:1]))
    if clue_matches:
        groups.append(_build_group("关键线索", clue_matches[:2]))
    if mission_matches:
        groups.append(_build_group("核心任务", mission_matches[:2]))
    return groups


def build_story_seed_map(idea: str) -> dict[str, str]:
    seeds: dict[str, str] = {}
    for group in extract_story_anchor_groups(idea):
        if group["primary"]:
            seeds[group["label"]] = group["primary"]
    return seeds


def evaluate_story_alignment(text: str, idea: str, stage: str) -> dict[str, Any]:
    groups = [group for group in extract_story_anchor_groups(idea) if stage in group["stages"]]
    cleaned = (text or "").strip()

    if not groups:
        return {
            "groups": [],
            "matched_groups": [],
            "missing_groups": [],
            "required_missing": [],
            "matched_count": 0,
            "total_groups": 0,
            "score": 1.0,
            "is_valid": True,
        }

    matched_groups: list[dict[str, Any]] = []
    missing_groups: list[dict[str, Any]] = []
    for group in groups:
        if any(term and term in cleaned for term in group["variants"]):
            matched_groups.append(group)
        else:
            missing_groups.append(group)

    required_labels: set[str] = set()
    if any(group["label"] == "主角身份" for group in groups):
        required_labels.add("主角身份")
    if stage in {"outline", "script"} and any(group["label"] == "关键场域" for group in groups):
        required_labels.add("关键场域")

    required_missing = [group for group in missing_groups if group["label"] in required_labels]

    min_match_by_stage = {
        "characters": 2,
        "outline": 3,
        "script": 2,
    }
    required_match_count = min(len(groups), min_match_by_stage.get(stage, 2))
    matched_count = len(matched_groups)
    score = matched_count / len(groups) if groups else 1.0
    enough_groups = matched_count >= required_match_count

    return {
        "groups": groups,
        "matched_groups": matched_groups,
        "missing_groups": missing_groups,
        "required_missing": required_missing,
        "matched_count": matched_count,
        "total_groups": len(groups),
        "required_match_count": required_match_count,
        "score": round(score, 2),
        "is_valid": enough_groups and not required_missing,
    }


def build_story_guardrail_block(idea: str, stage: str) -> str:
    groups = [group for group in extract_story_anchor_groups(idea) if stage in group["stages"]]
    if not groups:
        return f"核心设定原文：{(idea or '').strip()}"

    lines = ["以下题设锚点必须保留，不得偷换："]
    for group in groups:
        lines.append(f"- {group['label']}：{'、'.join(group['terms'])}")
    lines.append("允许你扩写细节，但不允许把职业、关系、地点、线索或任务改写成别的设定。")
    return "\n".join(lines)
