import re
from typing import Any

from app.core.script_formats import (
    DEFAULT_SCRIPT_FORMAT,
    build_act_label_pattern,
    get_act_sequence,
    get_script_format_label,
)
from app.core.story_constraints import evaluate_story_alignment


class NarrativeRuleEngine:
    """Lightweight validation for on-topic narrative generation."""

    ARC_KEYWORDS = ["觉醒", "挣扎", "成长", "蜕变", "和解", "牺牲"]

    def evaluate(
        self,
        text: str,
        *,
        stage: str,
        idea: str = "",
        characters: str = "",
        script_format: str = DEFAULT_SCRIPT_FORMAT,
    ) -> dict[str, Any]:
        cleaned = (text or "").strip()
        alignment = evaluate_story_alignment(cleaned, idea, stage) if idea else None
        hard_errors = self._hard_checks(
            cleaned,
            stage=stage,
            idea=idea,
            characters=characters,
            alignment=alignment,
            script_format=script_format,
        )
        soft_warnings = self._soft_checks(cleaned, stage=stage)
        metrics = self._build_metrics(
            cleaned,
            stage=stage,
            hard_errors=hard_errors,
            soft_warnings=soft_warnings,
            alignment=alignment,
        )

        return {
            "stage": stage,
            "is_valid": len(hard_errors) == 0,
            "hard_errors": hard_errors,
            "soft_warnings": soft_warnings,
            "metrics": metrics,
        }

    def _hard_checks(
        self,
        text: str,
        *,
        stage: str,
        idea: str,
        characters: str,
        alignment: dict[str, Any] | None,
        script_format: str,
    ) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []

        if not text:
            return [
                {
                    "code": "EMPTY_OUTPUT",
                    "description": "模型返回为空，当前阶段没有产出可用内容。",
                    "fix_instruction": "请直接输出当前阶段的完整中文结果，不要留空。",
                }
            ]

        if alignment and not alignment.get("is_valid", True):
            missing_groups = alignment.get("missing_groups") or []
            required_missing = alignment.get("required_missing") or []
            if required_missing:
                for group in required_missing:
                    primary = group.get("primary") or "题设核心锚点"
                    errors.append(
                        {
                            "code": "IDEA_ANCHOR_REQUIRED_MISSING",
                            "description": f"输出没有保留题设中的关键锚点：{group.get('label', '核心锚点')}（{primary}）。",
                            "fix_instruction": f"必须明确保留并落地“{primary}”这一题设，不得改成其他职业、地点、关系或事件。",
                        }
                    )

            matched_count = int(alignment.get("matched_count") or 0)
            required_match_count = int(alignment.get("required_match_count") or 0)
            if matched_count < required_match_count and missing_groups:
                preview = "、".join(group.get("primary", "") for group in missing_groups[:3] if group.get("primary"))
                errors.append(
                    {
                        "code": "IDEA_ALIGNMENT_LOW",
                        "description": "输出虽然成文，但与原始题设的关键设定贴合度不足。",
                        "fix_instruction": f"请围绕题设重写，并至少补齐这些核心锚点：{preview or '主角身份、关键场域、核心任务'}。",
                    }
                )

        if stage == "outline":
            required = get_act_sequence(script_format)
            if not all(item in text for item in required):
                structure_text = "、".join(required)
                errors.append(
                    {
                        "code": "OUTLINE_STRUCTURE_MISSING",
                        "description": f"大纲缺少完整的“{get_script_format_label(script_format)}”结构。",
                        "fix_instruction": f"请补齐“{structure_text}”，并写清每一幕的推进和升级。",
                    }
                )

        if stage == "script":
            scene_hits = len(re.findall(r"^(内景|外景)", text, flags=re.MULTILINE))
            if scene_hits < 1:
                errors.append(
                    {
                        "code": "SCENE_HEADER_MISSING",
                        "description": "剧本缺少有效的场景标题，无法形成可拍摄的分场。",
                        "fix_instruction": "请至少写出一场戏，并使用“内景/外景 + 场所 + 时间”的中文场景标题。",
                    }
                )

            act_section_hits = len(
                re.findall(rf"{build_act_label_pattern(script_format)}[·.、 ]?第[一二三四五六七八九十百\d]+节", text)
            )
            if act_section_hits == 0:
                errors.append(
                    {
                        "code": "ACT_SECTION_MISSING",
                        "description": "剧本缺少“第几幕·第几节”这一结构标记。",
                        "fix_instruction": f"请在每场戏前写清“{get_act_sequence(script_format)[0]}·第1节”这类标签，并与场次对应。",
                    }
                )

            scene_numbers = [
                int(match)
                for match in re.findall(r"^第(\d+)场", text, flags=re.MULTILINE)
            ]
            if scene_numbers:
                if len(scene_numbers) != len(set(scene_numbers)) or scene_numbers != sorted(scene_numbers):
                    errors.append(
                        {
                            "code": "SCENE_NUMBER_DISORDERED",
                            "description": "场次编号出现重复或顺序错乱，容易导致同一场标题重复叠加。",
                            "fix_instruction": "请让场次编号严格顺延，每个“第X场”只出现一次，不要重复使用同一个场次编号。",
                        }
                    )

            scaffold_markers = ["校验备注：", "上一场位于：", "当前目标："]
            if any(marker in text for marker in scaffold_markers):
                errors.append(
                    {
                        "code": "SCRIPT_SCAFFOLD_LEAK",
                        "description": "剧本正文混入了内部续写脚手架提示语。",
                        "fix_instruction": "请删除“校验备注/上一场位于/当前目标”等内部提示，只保留真正发生的场次内容。",
                    }
                )

            if re.search(r"(?m)^主角\s*$", text):
                errors.append(
                    {
                        "code": "PLACEHOLDER_CHARACTER_NAME",
                        "description": "剧本里出现了“主角”这类占位角色名，说明内容还没完全成稿。",
                        "fix_instruction": "请使用真实角色名，不要把“主角/对手/协助者”当成对白说话人。",
                    }
                )

            has_dialogue = bool(
                re.search(r"(^[\u4e00-\u9fff]{2,6}\s*$\n.+)|([\u4e00-\u9fff]{2,6}[：:])", text, flags=re.MULTILINE)
            )
            if not has_dialogue:
                errors.append(
                    {
                        "code": "DIALOGUE_MISSING",
                        "description": "剧本缺少有效人物对白。",
                        "fix_instruction": "请加入明确的人物对白，让角色通过对白推动冲突和信息揭示。",
                    }
                )

        foreshadow_count = text.count("伏笔")
        recovery_count = text.count("回收")
        if foreshadow_count > 0 and recovery_count == 0 and stage in {"outline", "script"}:
            errors.append(
                {
                    "code": "FORESHADOW_NOT_RECOVERED",
                    "description": "文本提到了伏笔，但没有交代任何回收方向。",
                    "fix_instruction": "请补充至少一个伏笔回收点，或者明确后续如何兑现它。",
                }
            )

        expected_names = self._extract_character_names(characters)
        if expected_names and stage in {"outline", "script"}:
            covered = [name for name in expected_names if name in text]
            if len(covered) == 0:
                errors.append(
                    {
                        "code": "CHARACTER_INCONSISTENT",
                        "description": "生成内容没有承接前面的人物设定，核心角色名完全缺失。",
                        "fix_instruction": f"请至少让这些角色中的一位进入当前内容：{'、'.join(expected_names[:3])}。",
                    }
                )

        return errors

    def _soft_checks(self, text: str, *, stage: str) -> list[dict[str, str]]:
        warnings: list[dict[str, str]] = []

        if stage in {"outline", "script"}:
            conflict_hits = len(re.findall(r"冲突|对抗|矛盾|危机|代价|威胁", text))
            if conflict_hits < 2:
                warnings.append(
                    {
                        "code": "LOW_CONFLICT_DENSITY",
                        "description": "冲突密度偏低，建议增加对抗、代价或价值碰撞。",
                    }
                )

            arc_hits = sum(1 for key in self.ARC_KEYWORDS if key in text)
            if arc_hits < 2:
                warnings.append(
                    {
                        "code": "WEAK_ARC_SIGNAL",
                        "description": "人物弧光信号较弱，建议补足“觉醒-挣扎-蜕变”的变化路径。",
                    }
                )

        if stage == "script":
            scene_hits = len(re.findall(r"^第[一二三四五六七八九十百\d]+场", text, flags=re.MULTILINE))
            if scene_hits < 2:
                warnings.append(
                    {
                        "code": "SCENE_COUNT_LOW",
                        "description": "本幕分场数量偏少，建议至少两场以保证节奏推进。",
                    }
                )

        return warnings

    def _build_metrics(
        self,
        text: str,
        *,
        stage: str,
        hard_errors: list[dict[str, str]],
        soft_warnings: list[dict[str, str]],
        alignment: dict[str, Any] | None,
    ) -> dict[str, Any]:
        scene_hits = len(re.findall(r"^(内景|外景)", text, flags=re.MULTILINE))
        numbered_scene_hits = len(re.findall(r"^第[一二三四五六七八九十百\d]+场", text, flags=re.MULTILINE))
        foreshadow_count = text.count("伏笔")
        recovery_count = text.count("回收")

        foreshadow_ratio = 100.0 if foreshadow_count == 0 else min(100.0, recovery_count / foreshadow_count * 100)
        compliance = 100.0 if not hard_errors else max(0.0, 100.0 - len(hard_errors) * 25)
        creative_score = max(60.0, 100.0 - len(soft_warnings) * 10)

        metrics: dict[str, Any] = {
            "stage": stage,
            "scene_count": scene_hits,
            "numbered_scene_count": numbered_scene_hits,
            "foreshadow_count": foreshadow_count,
            "recovery_count": recovery_count,
            "foreshadow_recovery_rate": round(foreshadow_ratio, 1),
            "hard_compliance_score": round(compliance, 1),
            "creative_reference_score": round(creative_score, 1),
        }

        if alignment:
            metrics.update(
                {
                    "idea_alignment_score": round(float(alignment.get("score") or 0.0) * 100, 1),
                    "matched_anchor_groups": int(alignment.get("matched_count") or 0),
                    "total_anchor_groups": int(alignment.get("total_groups") or 0),
                    "matched_anchor_labels": [group.get("label", "") for group in alignment.get("matched_groups", [])],
                    "missing_anchor_labels": [group.get("label", "") for group in alignment.get("missing_groups", [])],
                }
            )

        return metrics

    def _extract_character_names(self, characters: str) -> list[str]:
        names: list[str] = []
        text = characters or ""

        patterns = [
            r"(?:姓名|名字)[：:]\s*([\u4e00-\u9fff]{2,6})",
            r"^[0-9一二三四五六七八九十]+[\.、]\s*([\u4e00-\u9fff]{2,4})",
            r"^([\u4e00-\u9fff]{2,4})[（(]",
        ]

        for pattern in patterns:
            for match in re.findall(pattern, text, flags=re.MULTILINE):
                if match not in names:
                    names.append(match)

        return names
