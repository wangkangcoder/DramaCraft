import unittest
from unittest.mock import patch
from pathlib import Path

from app.api.ai import (
    build_characters_prompt,
    build_outline_prompt,
    enforce_script_labels,
)
from app.api.narrative import (
    _build_current_act_review,
    _build_current_act_revision_prompt,
    _build_completion_fallback,
    _generate_complete_act_candidate,
    _build_next_act_result,
    _build_next_act_text,
    _estimate_outline_item_coverage,
    _extract_current_act_context,
    _build_next_act_prompt,
    _extract_focus_keywords,
    _extract_outline_items,
    _revise_current_act,
    _strip_internal_scaffolding,
)
from app.core.rule_engine import NarrativeRuleEngine
from app.core.story_constraints import extract_story_anchor_groups


IDEA = (
    "\u8fd1\u672a\u6765\u6d77\u6e2f\u57ce\u5e02\u91cc\uff0c\u4e00\u540d\u5973\u5de5\u7a0b\u5e08\u6536\u5230"
    "\u5931\u8e2a\u54e5\u54e5\u7559\u4e0b\u7684\u6c42\u6551\u4fe1\u53f7\uff0c\u5fc5\u987b\u6f5c\u5165"
    "\u5c01\u95ed\u5b9e\u9a8c\u7ad9\u63ed\u5f00\u4e8b\u6545\u771f\u76f8\u3002"
)


class StoryAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = NarrativeRuleEngine()

    def test_extract_story_anchor_groups(self) -> None:
        groups = {group["label"]: group["terms"] for group in extract_story_anchor_groups(IDEA)}
        self.assertIn("\u4e3b\u89d2\u8eab\u4efd", groups)
        self.assertIn("\u5173\u952e\u573a\u57df", groups)
        self.assertIn("\u6838\u5fc3\u5173\u7cfb", groups)
        self.assertIn("\u5173\u952e\u7ebf\u7d22", groups)
        self.assertIn("\u6838\u5fc3\u4efb\u52a1", groups)
        self.assertIn("\u5973\u5de5\u7a0b\u5e08", groups["\u4e3b\u89d2\u8eab\u4efd"])

    def test_rule_engine_rejects_drifted_characters(self) -> None:
        drifted = (
            "\u4e3b\u89d2\n"
            "\u59d3\u540d\uff1a\u6797\u9ed8 \u8eab\u4efd\uff1a\u524d\u5211\u8b66\uff0c\u73b0\u4e3a\u79c1\u5bb6\u4fa6\u63a2 "
            "\u76ee\u6807\uff1a\u8c03\u67e5\u72af\u7f6a\u96c6\u56e2\u6d17\u94b1\u6848\n"
        )
        result = self.engine.evaluate(drifted, stage="characters", idea=IDEA)
        self.assertFalse(result["is_valid"])
        self.assertTrue(
            any(error["code"] in {"IDEA_ANCHOR_REQUIRED_MISSING", "IDEA_ALIGNMENT_LOW"} for error in result["hard_errors"])
        )

    def test_rule_engine_accepts_on_topic_characters(self) -> None:
        on_topic = (
            "\u4e3b\u89d2\n"
            "\u59d3\u540d\uff1a\u6c88\u5c9a \u8eab\u4efd\uff1a\u5973\u5de5\u7a0b\u5e08 "
            "\u76ee\u6807\uff1a\u6839\u636e\u5931\u8e2a\u54e5\u54e5\u7559\u4e0b\u7684\u6c42\u6551\u4fe1\u53f7\uff0c"
            "\u6f5c\u5165\u5c01\u95ed\u5b9e\u9a8c\u7ad9\u63ed\u5f00\u4e8b\u6545\u771f\u76f8\n\n"
            "\u5bf9\u624b\u4eba\u7269\n"
            "\u59d3\u540d\uff1a\u987e\u60df \u8eab\u4efd\uff1a\u6d77\u6e2f\u57ce\u5e02\u5b9e\u9a8c\u7ad9\u7684\u5b89\u4fdd\u8d1f\u8d23\u4eba\n"
            "\u76ee\u6807\uff1a\u963b\u6b62\u6c88\u5c9a\u7ee7\u7eed\u8c03\u67e5"
        )
        result = self.engine.evaluate(on_topic, stage="characters", idea=IDEA)
        self.assertTrue(result["is_valid"], result)

    def test_rule_engine_rejects_script_scaffold_leak(self) -> None:
        scaffold_script = (
            "\u7b2c\u4e00\u5e55\u00b7\u7b2c1\u8282\n"
            "\u7b2c1\u573a\n"
            "\u5185\u666f \u4e34\u65f6\u63a7\u5236\u5ba4 \u591c\n"
            "\u4e0a\u4e00\u573a\u4f4d\u4e8e\uff1a\u5185\u666f \u4e34\u65f6\u7a7a\u95f4 \u591c\n"
            "\u5f53\u524d\u76ee\u6807\uff1a\u5973\u5de5\u7a0b\u5e08\u6536\u5230\u54e5\u54e5\u7684\u6c42\u6551\u4fe1\u53f7\n"
            "\u6821\u9a8c\u5907\u6ce8\uff1a\u65b0\u573a\u6b21\u6ca1\u6709\u771f\u6b63\u63a8\u8fdb\u5f53\u524d\u5e94\u5199\u7684\u5927\u7eb2\u8282\u70b9\n"
            "\u52a8\u4f5c\u63cf\u8ff0\n"
            "\u4e3b\u89d2\u6ca1\u6709\u505c\u7559\u5728\u4e0a\u4e00\u573a\u7684\u60c5\u7eea\u91cc\u3002\n"
            "\u4e3b\u89d2\n"
            "\u8fd9\u4e00\u6b21\uff0c\u6211\u4eec\u4e0d\u80fd\u518d\u539f\u5730\u6253\u8f6c\u4e86\u3002"
        )
        result = self.engine.evaluate(
            scaffold_script,
            stage="script",
            idea=IDEA,
            characters="\u59d3\u540d\uff1a\u6797\u8587",
        )
        self.assertFalse(result["is_valid"])
        self.assertTrue(any(error["code"] == "SCRIPT_SCAFFOLD_LEAK" for error in result["hard_errors"]))

    def test_strip_internal_scaffolding_removes_generation_meta(self) -> None:
        dirty = (
            "第一幕·第2节\n"
            "第3场\n"
            "内景 临时控制室 夜\n"
            "上一场位于：外景 暴雨甲板 夜\n"
            "当前目标：林薇确认求救信号源来自深海实验站\n"
            "校验备注：新场次没有真正推进当前应写的大纲节点\n"
            "动作描述\n"
            "林薇将波形图叠上深海基站频率，终于锁定实验站坐标。\n"
            "林薇\n"
            "这一次，我们不能再原地打转了。\n"
        )
        cleaned = _strip_internal_scaffolding(dirty)
        self.assertIn("第一幕·第2节", cleaned)
        self.assertIn("第3场", cleaned)
        self.assertIn("内景 临时控制室 夜", cleaned)
        self.assertIn("林薇将波形图叠上深海基站频率", cleaned)
        self.assertNotIn("上一场位于：", cleaned)
        self.assertNotIn("当前目标：", cleaned)
        self.assertNotIn("校验备注：", cleaned)
        self.assertNotIn("动作描述", cleaned)
        self.assertNotIn("这一次，我们不能再原地打转了。", cleaned)

    def test_rule_engine_rejects_duplicate_scene_numbers(self) -> None:
        duplicated = (
            "第一幕·第1节\n"
            "第1场\n"
            "外景 青雾城街道 夜\n"
            "林薇沿着空街狂奔。\n"
            "林薇\n"
            "信号就在前面。\n\n"
            "第一幕·第2节\n"
            "第1场\n"
            "内景 图书馆工作间 夜\n"
            "林薇把设备重重砸在桌上。\n"
            "林薇\n"
            "我不会再错过这次机会。\n"
        )
        result = self.engine.evaluate(duplicated, stage="script", idea=IDEA, characters="姓名：林薇")
        self.assertFalse(result["is_valid"])
        self.assertTrue(any(error["code"] == "SCENE_NUMBER_DISORDERED" for error in result["hard_errors"]))

    def test_enforce_script_labels_rebuilds_duplicate_inline_headers(self) -> None:
        messy = (
            "第一幕·第1节 第1场 外景 青雾城街道 夜\n"
            "林薇撞开雨雾，顺着信号追向旧城区。\n"
            "第一幕·第1节 第1场 内景 青雾市立图书馆 工作间 夜\n"
            "她把失真的波形投到墙上。\n"
            "第一幕·第2节 第1场 外景 老街区河岸步道 夜\n"
            "信号在水面反光里突然变强。\n"
        )
        rebuilt = enforce_script_labels(messy, default_act_label="第一幕", start_scene_index=1, max_sections=3, single_act=True)
        self.assertIn("第一幕·第1节\n第1场\n外景 青雾城街道 夜", rebuilt)
        self.assertIn("第2场\n内景 青雾市立图书馆 工作间 夜", rebuilt)
        self.assertIn("第一幕·第2节\n第3场\n外景 老街区河岸步道 夜", rebuilt)
        self.assertEqual(rebuilt.count("第1场"), 1)

    def test_prompt_includes_guardrails(self) -> None:
        prompt = build_characters_prompt(IDEA)
        self.assertIn("\u4ee5\u4e0b\u9898\u8bbe\u951a\u70b9\u5fc5\u987b\u4fdd\u7559", prompt)
        self.assertIn("\u5973\u5de5\u7a0b\u5e08", prompt)
        self.assertIn("\u5c01\u95ed\u5b9e\u9a8c\u7ad9", prompt)

    def test_outline_prompt_uses_series_structure(self) -> None:
        prompt = build_outline_prompt(IDEA, "姓名：沈岚；身份：女工程师", script_format="series")
        self.assertIn("电视/连续剧", prompt)
        self.assertIn("第四幕", prompt)
        self.assertIn("解决危机 + 留下新悬念", prompt)

    def test_rule_engine_requires_selected_outline_structure(self) -> None:
        incomplete_series_outline = (
            "第一幕：林薇收到求救信号并意识到自己必须回到实验站。"
            "第二幕：她开始行动，却很快被旧势力盯上。"
            "第三幕：她被逼入绝境，差点失去唯一同伴。"
        )
        result = self.engine.evaluate(incomplete_series_outline, stage="outline", idea=IDEA, script_format="series")
        self.assertFalse(result["is_valid"])
        self.assertTrue(any(error["code"] == "OUTLINE_STRUCTURE_MISSING" for error in result["hard_errors"]))

    def test_narrative_keywords_keep_semantic_anchors(self) -> None:
        keywords = _extract_focus_keywords(IDEA, limit=8)
        joined = " ".join(keywords)
        self.assertIn("\u5de5\u7a0b\u5e08", joined)
        self.assertIn("\u6d77\u6e2f", joined)
        self.assertIn("\u5b9e\u9a8c\u7ad9", joined)
        self.assertIn("\u6c42\u6551\u4fe1\u53f7", joined)

    def test_outline_items_do_not_split_minor_clauses(self) -> None:
        outline = (
            "\u7b2c\u4e00\u5e55\uff1a\u5973\u5de5\u7a0b\u5e08\u6797\u8587\u5728\u8fd1\u672a\u6765\u6d77\u6e2f\u57ce\u5e02"
            "\u63a5\u6536\u5230\u5931\u8e2a\u54e5\u54e5\u7684\u6c42\u6551\u4fe1\u53f7\uff0c\u4fe1\u53f7\u6307\u5411"
            "\u88ab\u5c01\u9501\u7684\u6df1\u6d77\u5b9e\u9a8c\u7ad9\uff0c\u4f46\u7f3a\u4e4f\u7279\u5de5\u8bad\u7ec3\u3002"
        )
        items = _extract_outline_items(outline)
        self.assertEqual(len(items), 1)
        self.assertIn("\u63a5\u6536\u5230\u5931\u8e2a\u54e5\u54e5\u7684\u6c42\u6551\u4fe1\u53f7", items[0]["text"])

    def test_outline_items_are_capped_to_three_targets_per_act(self) -> None:
        outline = (
            "\u7b2c\u4e00\u5e55\n"
            "\u6797\u9759\u5728\u7ef4\u62a4\u57ce\u5e02\u80fd\u6e90\u7f51\u7edc\u3002"
            "\u5979\u6536\u5230\u5931\u8e2a\u54e5\u54e5\u7684\u6c42\u6551\u4fe1\u53f7\u3002"
            "\u4fe1\u53f7\u6307\u5411\u88ab\u5c01\u9501\u7684\u76d8\u53e4\u5b9e\u9a8c\u7ad9\u3002"
            "\u5979\u7533\u8bf7\u901a\u884c\u88ab\u62d2\u3002"
            "\u5979\u627e\u5230\u8001\u5468\u5e76\u62ff\u5230\u5e9f\u5f03\u7ba1\u9053\u56fe\u3002"
            "\u9648\u701a\u5f00\u59cb\u8ffd\u67e5\u63a5\u89e6\u5b9e\u9a8c\u7ad9\u7684\u5916\u90e8\u4eba\u5458\u3002\n"
            "\u7b2c\u4e8c\u5e55\n"
            "\u6797\u9759\u6f5c\u5165\u6392\u6c34\u7cfb\u7edf\u3002"
            "\u5979\u8e72\u5f00\u4f20\u611f\u5668\u5e76\u63a5\u8fd1\u5e9f\u5f03\u7ba1\u9053\u3002"
            "\u9648\u701a\u53d1\u73b0\u5165\u4fb5\u75d5\u8ff9\u540e\u5e26\u961f\u641c\u6355\u3002"
            "\u6797\u9759\u8fdb\u5165\u5b9e\u9a8c\u7ad9\u5730\u4e0b\u7f13\u51b2\u533a\u3002"
        )
        items = _extract_outline_items(outline)
        first_act_items = [item for item in items if item["section"] == "\u7b2c\u4e00\u5e55"]
        second_act_items = [item for item in items if item["section"] == "\u7b2c\u4e8c\u5e55"]

        self.assertEqual(len(first_act_items), 3)
        self.assertEqual(len(second_act_items), 3)
        self.assertIn("\u7ef4\u62a4\u57ce\u5e02\u80fd\u6e90\u7f51\u7edc", first_act_items[0]["text"])
        self.assertIn("\u627e\u5230\u8001\u5468", first_act_items[1]["text"])
        self.assertIn("\u6f5c\u5165\u6392\u6c34\u7cfb\u7edf", second_act_items[0]["text"])
        self.assertIn("\u8fdb\u5165\u5b9e\u9a8c\u7ad9\u5730\u4e0b\u7f13\u51b2\u533a", second_act_items[-1]["text"])

    def test_outline_coverage_accepts_multi_clause_macro_target(self) -> None:
        item = (
            "\u8fd1\u672a\u6765\u6e2f\u57ce\uff0c\u9ad8\u7ea7\u7ed3\u6784\u5de5\u7a0b\u5e08\u6797\u8587\u6536\u5230\u54e5\u54e5\u7684\u6c42\u6551\u4fe1\u53f7\uff1b"
            "\u4fe1\u53f7\u6307\u5411\u5df2\u5c01\u95ed\u7684\u6d77\u6e0a\u5b9e\u9a8c\u7ad9\uff1b"
            "\u5979\u4f7f\u7528\u5de5\u7a0b\u6743\u9650\u67e5\u8be2\u540e\u53d1\u73b0\u5b9e\u9a8c\u7ad9\u88ab\u5b89\u5168\u5c40\u5f7b\u5e95\u9501\u6b7b\uff1b"
            "\u7406\u6027\u544a\u8bc9\u5979\u64c5\u95ef\u540e\u679c\u4e25\u91cd\uff1b"
            "\u4f46\u5979\u8fd8\u662f\u51b3\u5b9a\u4ece\u7ef4\u62a4\u7ba1\u9053\u8fdb\u5165"
        )
        content = (
            "\u6797\u8587\u5728\u8fd1\u672a\u6765\u6e2f\u57ce\u7684\u8c03\u5ea6\u4e2d\u5fc3\u6536\u5230\u4e86\u54e5\u54e5\u7684\u6c42\u6551\u4fe1\u53f7\uff0c"
            "\u5750\u6807\u76f4\u6307\u88ab\u5c01\u95ed\u7684\u201c\u6d77\u6e0a\u201d\u5b9e\u9a8c\u7ad9\u3002"
            "\u5979\u8c03\u7528\u5de5\u7a0b\u5e08\u6743\u9650\u67e5\u8be2\uff0c\u5374\u53ea\u770b\u5230\u5b89\u5168\u7ba1\u7406\u5c40\u7684\u7edd\u5bf9\u5c01\u9501\u63d0\u793a\u3002"
            "\u5c3d\u7ba1\u660e\u77e5\u64c5\u95ef\u7981\u533a\u4f1a\u89e6\u72af\u91cd\u7f6a\uff0c\u5979\u8fd8\u662f\u51b3\u5b9a\u987a\u7740\u5e9f\u5f03\u7ef4\u62a4\u7ba1\u9053\u60f3\u529e\u6cd5\u8fdb\u53bb\u6551\u4eba\u3002"
        )
        coverage = _estimate_outline_item_coverage(item, content)
        self.assertTrue(coverage["covered"], coverage)

    def test_narrative_api_keeps_single_live_generation_path(self) -> None:
        source = Path("backend/app/api/narrative.py").read_text(encoding="utf-8")
        critical_defs = [
            "def _looks_like_outline_meta(",
            "def _split_outline_segments(",
            "def _extract_outline_items(",
            "def _extract_outline_progress(",
            "def _validate_generated_act(",
            "def _build_completion_fallback(",
            "def _build_next_act_prompt(",
            "def _build_next_act_text(",
            "def _generate_next_act(",
        ]
        for signature in critical_defs:
            self.assertEqual(
                source.count(signature),
                1,
                f"{signature} should only be defined once",
            )

    def test_ai_api_has_no_screenplay_template_fallbacks(self) -> None:
        source = Path("backend/app/api/ai.py").read_text(encoding="utf-8")
        self.assertNotIn("def build_character_fallback(", source)
        self.assertNotIn("def build_outline_fallback(", source)
        self.assertNotIn("def build_script_fallback(", source)
        self.assertNotIn("def build_script_prompt(", source)
        self.assertNotIn("def _generate_outline_aligned_opening(", source)
        self.assertNotIn("current_scene", source)
        self.assertNotIn('@router.post("/analyze-plot")', source)
        self.assertNotIn("def extract_suggestions_from_text(", source)
        self.assertNotIn("def build_plot_advice_fallback(", source)

    def test_next_act_prompt_includes_original_idea_guardrails(self) -> None:
        payload = _build_next_act_prompt(
            "第一幕·第1节\n第1场\n内景 林薇的公寓 夜\n林薇盯着求救信号波形。\n林薇\n这不是噪声。",
            "第一幕：林薇确认求救信号源来自被封锁的深海实验站。第二幕：林薇尝试申请实验站权限，却发现官方通道已经被彻底封死。",
            "姓名：林薇；身份：人工智能与机械系统工程师",
            idea=IDEA,
        )
        prompt = payload["prompt"]
        self.assertIn("最早核心设定", prompt)
        self.assertIn("题设锚点约束", prompt)
        self.assertIn("女工程师", prompt)
        self.assertIn("实验站", prompt)
        self.assertIn("下一幕", prompt)
        self.assertIn("最多分 3 节", prompt)
        self.assertIn("4000 字左右", prompt)
        self.assertIn("3500-4500 字之间", prompt)
        self.assertIn("必须完整写完本幕", prompt)

    @patch(
        "app.api.narrative.generate_clean_content_with_meta",
        return_value=(
            "承接上场\n"
            "上一场位于：内景 林薇的公寓 夜\n"
            "当前目标：林薇确认求救信号源来自被封锁的深海实验站\n"
            "第一幕·第1节\n"
            "第2场\n"
            "内景 林薇的公寓 夜\n"
            "动作描述\n"
            "林薇把求救信号的频率图和海底基站数据叠在一起，终于确认信号源来自被封锁的深海实验站。\n"
            "林薇\n"
            "信号没有漂移，它就是从深海实验站里发出来的。\n",
            None,
            {"finish_reason": "stop"},
        ),
    )
    def test_build_next_act_text_strips_internal_generation_labels(self, _mock_generate) -> None:
        content = (
            "第一幕·第1节\n"
            "第1场\n"
            "内景 林薇的公寓 夜\n"
            "林薇反复校准一段失真的求救波形，哥哥的呼吸声在噪点中若隐若现。\n"
            "林薇\n"
            "只要再给我一点时间，我就能把信号源锁出来。\n"
        )
        outline = (
            "第一幕：林薇确认求救信号源来自被封锁的深海实验站。"
            "第二幕：林薇尝试通过官方渠道申请实验站权限，却发现全部通道已被封死。"
        )

        next_act = _build_next_act_text(content, outline=outline, characters="姓名：林薇；身份：工程师")

        self.assertTrue(next_act.startswith("第二幕·第1节\n第2场\n内景 林薇的公寓 夜"))
        self.assertIn("确认信号源来自被封锁的深海实验站", next_act)
        self.assertNotIn("上一场位于：", next_act)
        self.assertNotIn("当前目标：", next_act)
        self.assertNotIn("动作描述", next_act)

    @patch(
        "app.api.narrative.generate_clean_content_with_meta",
        side_effect=[
            (
                "第二幕·第1节\n"
                "第3场\n"
                "内景 旧码头调度楼 傍晚\n"
                "陈默记起东侧房间后窗正对海面，窗外是一个狭窄的维修",
                None,
                {"finish_reason": "length"},
            ),
            (
                "通道，贴着外墙一路延伸到排水口。\n"
                "陈默\n"
                "只要能摸进去，东西就还有机会拿到。\n",
                None,
                {"finish_reason": "stop"},
            ),
        ],
    )
    def test_generate_complete_act_candidate_continues_after_length_cutoff(self, mock_generate) -> None:
        result = _generate_complete_act_candidate(
            "请完整写完第二幕。",
            act_label="第二幕",
            section_index=1,
            start_scene_index=3,
            fallback_heading="内景 旧码头调度楼 傍晚",
        )

        self.assertEqual(mock_generate.call_count, 2)
        self.assertIn("第二幕·第1节", result)
        self.assertIn("窗外是一个狭窄的维修通道", result)
        self.assertIn("只要能摸进去", result)

    @patch(
        "app.api.narrative.generate_clean_content_with_meta",
        return_value=(
            "第一幕·第2节\n"
            "第3场\n"
            "内景 高校教室 夜\n"
            "年轻学生在教室里讨论校园比赛。\n"
            "学生\n"
            "今晚先别去海边了。\n",
            None,
            {"finish_reason": "stop"},
        ),
    )
    def test_build_next_act_result_keeps_candidate_when_it_drifted_from_original_idea(self, _mock_generate) -> None:
        content = (
            "第一幕·第1节\n"
            "第1场\n"
            "内景 林薇的公寓 夜\n"
            "林薇截获哥哥的求救信号，发现坐标指向深海实验站。\n"
            "林薇\n"
            "我得把这串频率解开。\n"
        )
        outline = (
            "第一幕：林薇确认求救信号源来自被封锁的深海实验站。"
            "第二幕：林薇尝试通过官方渠道申请实验站权限，却发现全部通道已被封死。"
        )

        result = _build_next_act_result(
            content,
            outline=outline,
            characters="姓名：林薇；身份：人工智能与机械系统工程师",
            idea=IDEA,
        )

        self.assertTrue(result["accepted_with_issues"], result)
        self.assertIn("高校教室", result["text"])
        self.assertTrue(
            any(fragment in result["reason"] for fragment in ("脱离了最早设定", "仍未完成本幕节点", "缺少核心锚点")),
            result,
        )

    @patch(
        "app.api.narrative.generate_clean_content",
        return_value=(
            '{"off_outline_summary":"这一方面没有明显问题。","off_outline_items":[],"summary":"当前幕主要问题是本幕大纲还没写完整。"}',
            None,
        ),
    )
    def test_current_act_review_reports_missing_outline_and_preserves_clean_side(self, _mock_generate) -> None:
        content = (
            "第一幕·第1节\n"
            "第1场\n"
            "内景 港口调度中心 夜\n"
            "林薇反复校验后，确认求救信号源来自被封锁的深海实验站。\n"
            "林薇\n"
            "信号源没错，就是那里。\n"
        )
        outline = (
            "第一幕：林薇确认求救信号源来自被封锁的深海实验站。"
            "林薇试图通过官方渠道联系实验站并申请探访权限。"
        )

        review = _build_current_act_review(
            content,
            outline=outline,
            characters="姓名：林薇；身份：人工智能与机械系统工程师",
            idea=IDEA,
        )

        self.assertEqual("第一幕", review["act_label"])
        self.assertTrue(review["enhancement"]["has_issue"], review)
        self.assertTrue(review["enhancement"]["items"], review)
        self.assertIn("polish", review)

    def test_completion_points_to_next_act_after_first_act_is_written(self) -> None:
        content = (
            "第一幕·第1节\n"
            "第1场\n"
            "内景 港口调度中心 夜\n"
            "林薇确认求救信号源来自被封锁的深海实验站。\n"
            "林薇\n"
            "信号源没错，就是那里。\n"
        )
        outline = (
            "第一幕：林薇确认求救信号源来自被封锁的深海实验站。"
            "林薇试图通过官方渠道申请探访权限。"
            "第二幕：林薇绕开官方封锁，冒险潜入实验站外围。"
        )

        completion = _build_completion_fallback(content, outline, script_format="movie")

        self.assertEqual("第一幕", completion["current_act_label"])
        self.assertEqual("第二幕", completion["next_act_label"])

    def test_current_act_revision_prompt_uses_ai_issue_checklist(self) -> None:
        content = (
            "第一幕·第1节\n"
            "第1场\n"
            "内景 港口调度中心 夜\n"
            "林薇确认求救信号源来自被封锁的深海实验站。\n"
            "年轻学生在教室里讨论校园比赛。\n"
        )
        outline = (
            "第一幕：林薇确认求救信号源来自被封锁的深海实验站。"
            "林薇试图通过官方渠道申请探访权限。"
        )
        context = _extract_current_act_context(content, outline)
        analysis = {
            "enhancement": {
                "has_issue": True,
                "summary": "当前幕还可以补强申请权限这一推进节点。",
                "items": [{"text": "林薇试图通过官方渠道申请探访权限。"}],
            },
            "polish": {
                "has_issue": True,
                "summary": "当前幕出现了与本幕目标无关的校园比赛内容。",
                "items": [
                    {
                        "problem": "出现了与当前幕目标无关的校园比赛内容",
                        "snippet": "年轻学生在教室里讨论校园比赛。",
                        "reason": "这一段没有推进申请权限，反而把注意力带离了本幕主线。",
                    }
                ],
            },
        }

        prompt = _build_current_act_revision_prompt(
            context,
            analysis,
            characters="姓名：林薇；身份：人工智能与机械系统工程师",
            idea=IDEA,
        )

        self.assertIn("优化建议 1", prompt)
        self.assertIn("优化建议 2", prompt)
        self.assertIn("原文片段：年轻学生在教室里讨论校园比赛。", prompt)
        self.assertIn("当前幕还可以补强什么", prompt)
        self.assertIn("哪些句子或段落可以改得更好", prompt)

    @patch(
        "app.api.narrative.generate_clean_content_with_meta",
        return_value=(
            "第一幕·第1节\n"
            "第1场\n"
            "内景 港口调度中心 夜\n"
            "林薇确认求救信号源来自被封锁的深海实验站后，林薇试图通过官方渠道申请探访权限。\n"
            "系统界面弹出红色封锁提示，所有官方通道都被彻底锁死。\n"
            "林薇\n"
            "既然正门被封死，我就得另找入口。\n",
            None,
            {"finish_reason": "stop"},
        ),
    )
    def test_revise_current_act_returns_generated_revision_directly(self, mock_generate) -> None:
        content = (
            "第一幕·第1节\n"
            "第1场\n"
            "内景 港口调度中心 夜\n"
            "林薇确认求救信号源来自被封锁的深海实验站。\n"
            "年轻学生在教室里讨论校园比赛。\n"
            "林薇\n"
            "我得先拿到通行许可。\n"
        )
        outline = (
            "第一幕：林薇确认求救信号源来自被封锁的深海实验站。"
            "林薇试图通过官方渠道申请探访权限。"
        )
        analysis = {
            "act_label": "第一幕",
            "has_issues": True,
            "missing_outline": {
                "has_issue": True,
                "summary": "当前幕还没完整覆盖申请权限这一节点。",
                "items": [{"text": "林薇试图通过官方渠道申请探访权限。"}],
            },
            "off_outline": {
                "has_issue": True,
                "summary": "当前幕出现了与本幕目标无关的校园比赛内容。",
                "items": [
                    {
                        "problem": "出现了与当前幕目标无关的校园比赛内容",
                        "snippet": "年轻学生在教室里讨论校园比赛。",
                        "reason": "这一段没有推进申请权限，反而把注意力带离了本幕主线。",
                    }
                ],
            },
            "summary": "当前幕同时存在缺失节点和脱纲内容。",
            "next_step": "继续生成修改版本。",
        }

        result = _revise_current_act(
            content,
            outline=outline,
            characters="姓名：林薇；身份：人工智能与机械系统工程师",
            idea=IDEA,
            analysis=analysis,
        )

        self.assertTrue(result["generated"], result)
        self.assertEqual(mock_generate.call_count, 1)
        self.assertIn("林薇试图通过官方渠道申请探访权限", result["revised_act"])
        self.assertNotIn("校园比赛", result["revised_act"])
        self.assertFalse(result["accepted_with_issues"], result)
        self.assertEqual("", result["warning"])

    @patch(
        "app.api.narrative.generate_clean_content_with_meta",
        side_effect=[
            (
                "",
                None,
                {"finish_reason": "stop"},
            ),
            (
                "第一幕·第1节\n"
                "第1场\n"
                "内景 港口调度中心 夜\n"
                "林薇确认求救信号源来自被封锁的深海实验站后，林薇试图通过官方渠道申请探访权限。\n"
                "林薇\n"
                "官方系统弹出封锁提示，她意识到正门已经彻底走不通。\n",
                None,
                {"finish_reason": "stop"},
            ),
        ],
    )
    def test_revise_current_act_retries_only_when_model_returns_no_revision_text(self, mock_generate) -> None:
        content = (
            "第一幕·第1节\n"
            "第1场\n"
            "内景 港口调度中心 夜\n"
            "林薇确认求救信号源来自被封锁的深海实验站。\n"
            "林薇\n"
            "我得先想办法进去。\n"
        )
        outline = (
            "第一幕：林薇确认求救信号源来自被封锁的深海实验站。"
            "林薇试图通过官方渠道申请探访权限。"
        )
        analysis = {
            "act_label": "第一幕",
            "has_issues": True,
            "missing_outline": {
                "has_issue": True,
                "summary": "当前幕还没完整覆盖申请权限这一节点。",
                "items": [{"text": "林薇试图通过官方渠道申请探访权限。"}],
            },
            "off_outline": {
                "has_issue": False,
                "summary": "这一方面没有明显问题。",
                "items": [],
            },
            "summary": "当前幕还没完整覆盖本幕大纲。",
            "next_step": "继续生成修改版本。",
        }

        result = _revise_current_act(
            content,
            outline=outline,
            characters="姓名：林薇；身份：人工智能与机械系统工程师",
            idea=IDEA,
            analysis=analysis,
        )

        self.assertTrue(result["generated"], result)
        self.assertEqual(mock_generate.call_count, 2)
        self.assertFalse(result["accepted_with_issues"], result)
        self.assertEqual("", result["warning"])
        self.assertIn("林薇确认求救信号源来自被封锁的深海实验站", result["revised_act"])


if __name__ == "__main__":
    unittest.main()
