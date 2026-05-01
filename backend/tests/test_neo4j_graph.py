import unittest

from app.models.neo4j_db import Neo4jDB


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
)


class FakeResult:
    def __init__(self, records=None):
        self.records = records or []

    def __iter__(self):
        return iter(self.records)

    def consume(self):
        return None


class FakeSession:
    def __init__(self):
        self.calls = []
        self.node_records = []
        self.link_records = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, statement, **params):
        self.calls.append((statement, params))
        if "RETURN n.entity_id AS id" in statement:
            return FakeResult(self.node_records)
        if "RETURN source.entity_id AS source" in statement:
            return FakeResult(self.link_records)
        return FakeResult()


class FakeDriver:
    def __init__(self):
        self.session_instance = FakeSession()

    def session(self):
        return self.session_instance


class Neo4jGraphTests(unittest.TestCase):
    def test_build_graph_payload_from_text_contains_role_scene_plot(self):
        db = Neo4jDB()
        payload = db.build_mock_graph_from_text(SCRIPT)

        categories = {node["category"] for node in payload["nodes"]}
        node_ids = {node["id"] for node in payload["nodes"]}

        self.assertIn(0, categories)
        self.assertIn(1, categories)
        self.assertIn(2, categories)
        self.assertTrue(any(node_id.startswith("char:") for node_id in node_ids))
        self.assertTrue(any(node_id.startswith("scene:") for node_id in node_ids))
        self.assertTrue(any(node_id.startswith("plot:") for node_id in node_ids))

    def test_persist_graph_payload_issues_real_neo4j_writes(self):
        db = Neo4jDB()
        fake_driver = FakeDriver()
        db.driver = fake_driver
        payload = db.build_mock_graph_from_text(SCRIPT)

        db._persist_graph_payload("active_screenplay", payload, SCRIPT)

        statements = "\n".join(call[0] for call in fake_driver.session_instance.calls)
        self.assertIn("ScreenplayGraph", statements)
        self.assertIn("GraphEntity:Character", statements)
        self.assertIn("GraphEntity:Scene", statements)
        self.assertIn("GraphEntity:PlotPoint", statements)
        self.assertIn("GRAPH_REL", statements)

    def test_query_graph_payload_reads_back_from_neo4j_shape(self):
        db = Neo4jDB()
        fake_driver = FakeDriver()
        fake_driver.session_instance.node_records = [
            {"id": "char:沈岚", "name": "沈岚", "category": 0, "sort_order": 0},
            {"id": "scene:港口调度中心", "name": "港口调度中心", "category": 1, "sort_order": 0},
            {"id": "plot:求救信号", "name": "求救信号", "category": 2, "sort_order": 0},
        ]
        fake_driver.session_instance.link_records = [
            {"source": "char:沈岚", "target": "scene:港口调度中心", "name": "出现在", "value": 1},
            {"source": "plot:求救信号", "target": "scene:港口调度中心", "name": "推动剧情", "value": 1},
        ]
        db.driver = fake_driver

        payload = db._query_graph_payload("active_screenplay")

        self.assertEqual(payload["storage_backend"], "neo4j")
        self.assertEqual(payload["graph_id"], "active_screenplay")
        self.assertEqual(len(payload["nodes"]), 3)
        self.assertEqual(len(payload["links"]), 2)

    def test_sync_graph_from_text_falls_back_when_driver_unavailable(self):
        db = Neo4jDB()
        db.connect = lambda: None
        db.driver = None

        payload = db.sync_graph_from_text(SCRIPT)

        self.assertEqual(payload["storage_backend"], "mock")
        self.assertTrue(payload["nodes"])
        self.assertTrue(payload["links"])


if __name__ == "__main__":
    unittest.main()
