import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.fingerprint import router as fingerprint_router
from app.core.fingerprint import analyze_narrative_fingerprint


SCRIPT = (
    "第一幕·第1节\n"
    "第1场\n"
    "内景 港口调度中心 夜\n"
    "沈岚反复校验哥哥留下的求救信号，发现坐标指向被封锁的深海实验站。\n"
    "沈岚\n"
    "信号不是噪声，它是有人故意留给我的路标。\n\n"
    "第2场\n"
    "外景 旧码头 雨夜\n"
    "顾南舟拦住沈岚，警告她实验站的事故真相会让所有人失控。\n"
    "顾南舟\n"
    "你再往前一步，就不是调查，是送命。\n"
)

OUTLINE = (
    "第一幕：沈岚确认求救信号来自被封锁的深海实验站，并意识到哥哥可能还活着。\n"
    "第二幕：她绕开官方封锁潜入实验站外围，逐步逼近事故真相。\n"
    "第三幕：真相曝光，沈岚必须在救人和阻止系统失控之间做出选择。"
)

CHARACTERS = (
    "姓名：沈岚\n"
    "身份：女工程师\n"
    "目标：根据哥哥留下的求救信号调查深海实验站事故真相\n\n"
    "姓名：顾南舟\n"
    "身份：实验站安保主管\n"
    "目标：阻止沈岚继续调查"
)


class FingerprintTests(unittest.TestCase):
    def test_analyze_narrative_fingerprint_returns_complete_payload(self) -> None:
        result = analyze_narrative_fingerprint(
            content=SCRIPT,
            outline=OUTLINE,
            characters=CHARACTERS,
            idea="近未来海港城市里，一名女工程师收到失踪哥哥留下的求救信号。",
            script_format="movie",
            title="深海回响",
        )

        self.assertTrue(result["analysis_id"].startswith("NF-MOV-"))
        self.assertEqual(result["title"], "深海回响")
        self.assertEqual(result["script_format"], "movie")
        self.assertEqual(len(result["dimensions"]), 5)
        self.assertGreaterEqual(result["score_panel"]["originality_score"], 0)
        self.assertGreaterEqual(result["score_panel"]["originality_score"], 85)
        self.assertEqual(result["score_panel"]["risk_level"], "green")
        self.assertEqual(result["score_panel"]["risk_label"], "极低风险")
        self.assertTrue(result["tempo_curve"])
        self.assertTrue(result["track_matches"])
        self.assertNotIn("similar_samples", result)
        self.assertNotIn("sample_library_info", result)

    def test_analyze_narrative_fingerprint_builds_character_graph_and_risk_items(self) -> None:
        result = analyze_narrative_fingerprint(
            content=SCRIPT,
            outline=OUTLINE,
            characters=CHARACTERS,
            script_format="movie",
        )

        graph = result["character_graph"]
        breakdown = result["story_breakdown"]
        node_names = {node["name"] for node in graph["nodes"]}

        self.assertIn("沈岚", node_names)
        self.assertIn("顾南舟", node_names)
        self.assertTrue(graph["links"])
        self.assertIn("strengths", breakdown)
        self.assertIn("recommendations", breakdown)
        self.assertIn("risks", breakdown)

    def test_fingerprint_api_endpoint_returns_success(self) -> None:
        app = FastAPI()
        app.include_router(fingerprint_router, prefix="/fingerprint")
        client = TestClient(app)

        response = client.post(
            "/fingerprint/analyze",
            json={
                "content": SCRIPT,
                "outline": OUTLINE,
                "characters": CHARACTERS,
                "script_format": "movie",
                "title": "深海回响",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertIn("analysis", payload)
        self.assertEqual(payload["analysis"]["title"], "深海回响")


if __name__ == "__main__":
    unittest.main()
