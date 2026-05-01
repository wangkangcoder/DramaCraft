from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Tuple

from neo4j import GraphDatabase

from app.core.config import settings


CHARACTER_STOP_WORDS = {
    "内景",
    "外景",
    "画外音",
    "动作",
    "场景",
    "镜头",
    "旁白",
    "系统",
    "提示",
    "当前",
    "台词",
}

PLOT_KEYWORDS = [
    "怀表",
    "录音",
    "求救信号",
    "旧照片",
    "钥匙",
    "档案",
    "密码",
    "芯片",
    "坐标",
    "信号",
    "门禁卡",
    "日志",
    "纸条",
    "船票",
    "手表",
    "真相",
    "事故",
    "线索",
    "证据",
    "任务",
    "危机",
]


class Neo4jDB:
    def __init__(self):
        self.uri = getattr(settings, "NEO4J_URI", "bolt://localhost:7687")
        self.user = getattr(settings, "NEO4J_USER", "neo4j")
        self.password = getattr(settings, "NEO4J_PASSWORD", "password")
        self.driver = None
        self.default_graph_id = "active_screenplay"
        self.mock_graph = self._default_graph()

    def _default_graph(self) -> dict[str, Any]:
        return {
            "graph_id": self.default_graph_id,
            "storage_backend": "mock",
            "nodes": [
                {"id": "char:主角", "name": "主角", "category": 0},
                {"id": "scene:当前场景", "name": "当前场景", "category": 1},
                {"id": "plot:关键线索", "name": "关键线索", "category": 2},
            ],
            "links": [
                {"source": "char:主角", "target": "scene:当前场景", "name": "出现在", "value": 1},
                {"source": "plot:关键线索", "target": "scene:当前场景", "name": "推动剧情", "value": 1},
            ],
        }

    def connect(self):
        if self.driver:
            return
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            verify_connectivity = getattr(self.driver, "verify_connectivity", None)
            if callable(verify_connectivity):
                verify_connectivity()
            self._ensure_schema()
            logging.info("Connected to Neo4j successfully.")
        except Exception as exc:
            logging.warning("Neo4j unavailable, fallback to parsed mock graph: %s", exc)
            if self.driver:
                try:
                    self.driver.close()
                except Exception:
                    pass
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()
            self.driver = None

    def _ensure_schema(self):
        if not self.driver:
            return

        statements = [
            "CREATE CONSTRAINT screenplay_graph_id IF NOT EXISTS FOR (g:ScreenplayGraph) REQUIRE g.graph_id IS UNIQUE",
            "CREATE INDEX graph_entity_lookup IF NOT EXISTS FOR (n:GraphEntity) ON (n.graph_id, n.entity_id)",
        ]
        with self.driver.session() as session:
            for statement in statements:
                session.run(statement).consume()

    def _clean_text(self, text: str) -> str:
        cleaned = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        cleaned = re.sub(r"[*#`_]+", "", cleaned)
        return cleaned.strip()

    def _clean_label(self, text: str, fallback: str) -> str:
        value = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9路·\- ]+", "", text or "").strip()
        return (value or fallback)[:24]

    def _add_node(
        self,
        nodes: Dict[str, Dict[str, Any]],
        node_id: str,
        name: str,
        category: int,
        sort_order: int,
    ):
        nodes[node_id] = {
            "id": node_id,
            "name": name,
            "category": category,
            "sort_order": sort_order,
        }

    def _add_link(
        self,
        links: Dict[Tuple[str, str, str], Dict[str, Any]],
        source: str,
        target: str,
        name: str,
        value: int = 1,
    ):
        key = (source, target, name)
        if key not in links:
            links[key] = {"source": source, "target": target, "name": name, "value": value}
        else:
            links[key]["value"] += value

    def _extract_scene_blocks(self, text: str) -> List[dict[str, Any]]:
        lines = [line.strip() for line in self._clean_text(text).split("\n") if line.strip()]
        blocks: List[dict[str, Any]] = []
        current_heading = ""
        current_lines: List[str] = []

        def flush():
            nonlocal current_heading, current_lines
            body = "\n".join(current_lines).strip()
            if body:
                blocks.append(
                    {
                        "heading": self._clean_label(current_heading, f"第{len(blocks) + 1}场"),
                        "text": body,
                    }
                )
            current_heading = ""
            current_lines = []

        for line in lines:
            if line.startswith(("内景", "外景")):
                if current_lines:
                    flush()
                current_heading = line
                current_lines = [line]
                continue

            if re.match(r"^第[\d一二三四五六七八九十百零]+场", line):
                if current_lines:
                    flush()
                current_heading = line
                current_lines = [line]
                continue

            current_lines.append(line)

        if current_lines:
            flush()

        if not blocks:
            fallback = self._clean_label(lines[0], "当前场景") if lines else "当前场景"
            blocks.append({"heading": fallback, "text": self._clean_text(text)})
        return blocks[:8]

    def _extract_scenes(self, text: str) -> List[str]:
        return [block["heading"] for block in self._extract_scene_blocks(text)]

    def _extract_characters(self, text: str) -> List[str]:
        cleaned = self._clean_text(text)
        candidates = []

        for match in re.findall(r"^([\u4e00-\u9fff]{2,4})[:：]?", cleaned, flags=re.MULTILINE):
            if match not in CHARACTER_STOP_WORDS:
                candidates.append(match)

        if not candidates:
            freq: Dict[str, int] = {}
            for token in re.findall(r"[\u4e00-\u9fff]{2,3}", cleaned):
                if token in CHARACTER_STOP_WORDS:
                    continue
                freq[token] = freq.get(token, 0) + 1
            candidates = [token for token, count in sorted(freq.items(), key=lambda item: item[1], reverse=True) if count >= 2]

        deduped = []
        for name in candidates:
            if name not in deduped:
                deduped.append(name)

        return deduped[:6] or ["主角"]

    def _extract_plot_points(self, text: str) -> List[str]:
        cleaned = self._clean_text(text)
        plot_points = []

        for keyword in PLOT_KEYWORDS:
            if keyword in cleaned:
                plot_points.append(keyword)

        bracket_hits = re.findall(r"[“\"（(]([^”\"）()]{1,12})[”\"）)]", cleaned)
        for item in bracket_hits:
            candidate = self._clean_label(item, "")
            if candidate and 1 < len(candidate) <= 12:
                plot_points.append(candidate)

        deduped = []
        for item in plot_points:
            if item not in deduped:
                deduped.append(item)

        return deduped[:6]

    def _build_graph_payload_from_text(self, text: str) -> dict[str, Any]:
        cleaned = self._clean_text(text)
        if not cleaned:
            self.mock_graph = self._default_graph()
            return self.mock_graph

        nodes: Dict[str, Dict[str, Any]] = {}
        links: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

        scene_blocks = self._extract_scene_blocks(cleaned)
        scenes = [block["heading"] for block in scene_blocks]
        characters = self._extract_characters(cleaned)
        plot_points = self._extract_plot_points(cleaned)

        for index, scene in enumerate(scenes):
            self._add_node(nodes, f"scene:{scene}", scene, 1, index)

        for index, character in enumerate(characters):
            self._add_node(nodes, f"char:{character}", character, 0, index)

        for index, plot_point in enumerate(plot_points):
            self._add_node(nodes, f"plot:{plot_point}", plot_point, 2, index)

        for scene_index, block in enumerate(scene_blocks):
            scene_id = f"scene:{block['heading']}"
            block_text = str(block.get("text") or "")
            scene_characters = [name for name in characters if name in block_text]
            if not scene_characters and characters:
                scene_characters = characters[:1]

            for character in scene_characters:
                self._add_link(links, f"char:{character}", scene_id, "出现在")

            for left_index, left_name in enumerate(scene_characters):
                for right_name in scene_characters[left_index + 1 :]:
                    self._add_link(links, f"char:{left_name}", f"char:{right_name}", "互动")

            for plot_point in plot_points:
                if plot_point in block_text:
                    self._add_link(links, f"plot:{plot_point}", scene_id, "推动剧情")

            if scene_index < len(scene_blocks) - 1:
                next_scene_id = f"scene:{scene_blocks[scene_index + 1]['heading']}"
                self._add_link(links, scene_id, next_scene_id, "推进到")

        payload = {
            "graph_id": self.default_graph_id,
            "storage_backend": "mock",
            "nodes": list(nodes.values()) or self._default_graph()["nodes"],
            "links": list(links.values()) or self._default_graph()["links"],
        }
        self.mock_graph = payload
        return payload

    def _serialize_node_batch(self, nodes: List[dict[str, Any]]) -> List[dict[str, Any]]:
        return [
            {
                "id": node["id"],
                "name": node["name"],
                "category": int(node["category"]),
                "sort_order": int(node.get("sort_order", 0)),
            }
            for node in nodes
        ]

    def _persist_graph_payload(self, graph_id: str, graph_payload: dict[str, Any], source_text: str) -> None:
        if not self.driver:
            raise RuntimeError("Neo4j driver is not available")

        nodes = list(graph_payload.get("nodes", []))
        character_nodes = [node for node in nodes if int(node.get("category", -1)) == 0]
        scene_nodes = [node for node in nodes if int(node.get("category", -1)) == 1]
        plot_nodes = [node for node in nodes if int(node.get("category", -1)) == 2]
        links = list(graph_payload.get("links", []))
        script_hash = hashlib.sha1(self._clean_text(source_text).encode("utf-8")).hexdigest()

        with self.driver.session() as session:
            session.run(
                """
                MERGE (g:ScreenplayGraph {graph_id: $graph_id})
                SET g.updated_at = datetime(),
                    g.script_hash = $script_hash,
                    g.node_count = $node_count,
                    g.link_count = $link_count
                WITH g
                OPTIONAL MATCH (g)-[:HAS_NODE]->(n:GraphEntity)
                DETACH DELETE n
                """,
                graph_id=graph_id,
                script_hash=script_hash,
                node_count=len(nodes),
                link_count=len(links),
            ).consume()

            if character_nodes:
                session.run(
                    """
                    MATCH (g:ScreenplayGraph {graph_id: $graph_id})
                    UNWIND $nodes AS node
                    CREATE (c:GraphEntity:Character {
                        graph_id: $graph_id,
                        entity_id: node.id,
                        name: node.name,
                        category: node.category,
                        sort_order: node.sort_order
                    })
                    MERGE (g)-[:HAS_NODE]->(c)
                    """,
                    graph_id=graph_id,
                    nodes=self._serialize_node_batch(character_nodes),
                ).consume()

            if scene_nodes:
                session.run(
                    """
                    MATCH (g:ScreenplayGraph {graph_id: $graph_id})
                    UNWIND $nodes AS node
                    CREATE (s:GraphEntity:Scene {
                        graph_id: $graph_id,
                        entity_id: node.id,
                        name: node.name,
                        category: node.category,
                        sort_order: node.sort_order
                    })
                    MERGE (g)-[:HAS_NODE]->(s)
                    """,
                    graph_id=graph_id,
                    nodes=self._serialize_node_batch(scene_nodes),
                ).consume()

            if plot_nodes:
                session.run(
                    """
                    MATCH (g:ScreenplayGraph {graph_id: $graph_id})
                    UNWIND $nodes AS node
                    CREATE (p:GraphEntity:PlotPoint {
                        graph_id: $graph_id,
                        entity_id: node.id,
                        name: node.name,
                        category: node.category,
                        sort_order: node.sort_order
                    })
                    MERGE (g)-[:HAS_NODE]->(p)
                    """,
                    graph_id=graph_id,
                    nodes=self._serialize_node_batch(plot_nodes),
                ).consume()

            if links:
                session.run(
                    """
                    UNWIND $links AS link
                    MATCH (source:GraphEntity {graph_id: $graph_id, entity_id: link.source})
                    MATCH (target:GraphEntity {graph_id: $graph_id, entity_id: link.target})
                    MERGE (source)-[r:GRAPH_REL {
                        graph_id: $graph_id,
                        rel_name: link.name,
                        source_id: link.source,
                        target_id: link.target
                    }]->(target)
                    SET r.name = link.name,
                        r.weight = coalesce(link.value, 1)
                    """,
                    graph_id=graph_id,
                    links=links,
                ).consume()

    def _query_graph_payload(self, graph_id: str) -> dict[str, Any]:
        if not self.driver:
            raise RuntimeError("Neo4j driver is not available")

        with self.driver.session() as session:
            node_records = list(
                session.run(
                    """
                    MATCH (:ScreenplayGraph {graph_id: $graph_id})-[:HAS_NODE]->(n:GraphEntity)
                    RETURN n.entity_id AS id, n.name AS name, n.category AS category, n.sort_order AS sort_order
                    ORDER BY n.category ASC, n.sort_order ASC, n.name ASC
                    """,
                    graph_id=graph_id,
                )
            )

            link_records = list(
                session.run(
                    """
                    MATCH (source:GraphEntity {graph_id: $graph_id})-[r:GRAPH_REL {graph_id: $graph_id}]->(target:GraphEntity {graph_id: $graph_id})
                    RETURN source.entity_id AS source, target.entity_id AS target, r.name AS name, r.weight AS value
                    ORDER BY source, target, name
                    """,
                    graph_id=graph_id,
                )
            )

        nodes = [
            {
                "id": record["id"],
                "name": record["name"],
                "category": int(record["category"] or 0),
                "sort_order": int(record["sort_order"] or 0),
            }
            for record in node_records
        ]
        links = [
            {
                "source": record["source"],
                "target": record["target"],
                "name": record["name"],
                "value": int(record["value"] or 1),
            }
            for record in link_records
        ]

        return {
            "graph_id": graph_id,
            "storage_backend": "neo4j",
            "nodes": nodes or self._default_graph()["nodes"],
            "links": links or self._default_graph()["links"],
        }

    def get_graph_snapshot(self, graph_id: str | None = None) -> dict[str, Any]:
        resolved_graph_id = (graph_id or self.default_graph_id).strip() or self.default_graph_id
        self.connect()

        if not self.driver:
            fallback = self.mock_graph or self._default_graph()
            fallback["graph_id"] = resolved_graph_id
            fallback["storage_backend"] = "mock"
            return fallback

        try:
            return self._query_graph_payload(resolved_graph_id)
        except Exception as exc:
            logging.warning("Failed to query Neo4j graph snapshot, fallback to mock graph: %s", exc)
            fallback = self.mock_graph or self._default_graph()
            fallback["graph_id"] = resolved_graph_id
            fallback["storage_backend"] = "mock"
            return fallback

    def sync_graph_from_text(self, text: str, graph_id: str | None = None) -> dict[str, Any]:
        resolved_graph_id = (graph_id or self.default_graph_id).strip() or self.default_graph_id
        graph_payload = self._build_graph_payload_from_text(text)
        graph_payload["graph_id"] = resolved_graph_id

        self.connect()
        if not self.driver:
            graph_payload["storage_backend"] = "mock"
            self.mock_graph = graph_payload
            return graph_payload

        try:
            self._persist_graph_payload(resolved_graph_id, graph_payload, text)
            queried_payload = self._query_graph_payload(resolved_graph_id)
            self.mock_graph = queried_payload
            return queried_payload
        except Exception as exc:
            logging.warning("Failed to persist/query Neo4j graph, fallback to parsed mock graph: %s", exc)
            graph_payload["storage_backend"] = "mock"
            self.mock_graph = graph_payload
            return graph_payload

    def build_mock_graph_from_text(self, text: str):
        return self._build_graph_payload_from_text(text)

    def simulate_function_call_update(self, text: str):
        logging.info("Syncing screenplay graph from text.")
        return self.sync_graph_from_text(text)


neo4j_client = Neo4jDB()
