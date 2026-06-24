"""
E2E tests for GET /graph/{owner}/{repo}
Uses the same indexed_client fixture pattern as test_api.py.
"""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.storage import knowledge_store

FIXTURE_SRC = """\
import os
from pathlib import Path

def add(x: int, y: int) -> int:
    \"\"\"Return x + y.\"\"\"
    return x + y

def multiply(x: int, y: int) -> int:
    return add(x, y) + add(x, y)

class Calculator:
    \"\"\"Simple calculator.\"\"\"

    def __init__(self):
        self.history = []

    @property
    def last(self):
        return self.history[-1] if self.history else None

    def compute(self, a, b):
        result = add(a, b)
        self.history.append(result)
        return result

    def double_compute(self, a, b):
        return self.compute(a, b) + self.compute(a, b)
"""

HELPER_SRC = """\
from math_utils import add

def triple(x: int) -> int:
    return add(x, add(x, x))
"""


@pytest.fixture(scope="module")
def fake_repo():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "math_utils.py").write_text(FIXTURE_SRC)
        (root / "helpers.py").write_text(HELPER_SRC)
        yield root


@pytest.fixture(scope="module")
def graph_client(fake_repo):
    knowledge_store.clear()
    with TestClient(app) as c:
        with patch("app.routers.index.clone_repo", return_value=fake_repo):
            resp = c.post("/index", json={"owner": "test", "repo": "graph"})
            assert resp.status_code == 200, resp.text
        yield c
    knowledge_store.clear()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestGraphErrors:
    def test_unindexed_repo_returns_404(self, graph_client):
        resp = graph_client.get("/graph/nobody/nothing?type=imports")
        assert resp.status_code == 404

    def test_invalid_type_returns_400(self, graph_client):
        resp = graph_client.get("/graph/test/graph?type=invalid")
        assert resp.status_code == 400

    def test_calls_without_root_returns_400(self, graph_client):
        resp = graph_client.get("/graph/test/graph?type=calls")
        assert resp.status_code == 400

    def test_unknown_root_returns_404(self, graph_client):
        resp = graph_client.get("/graph/test/graph?type=calls&root=nonexistent_fn")
        assert resp.status_code == 404

    def test_depth_too_large_returns_422(self, graph_client):
        resp = graph_client.get("/graph/test/graph?type=calls&root=multiply&depth=99")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Import graph
# ---------------------------------------------------------------------------

class TestImportGraph:
    def test_returns_200(self, graph_client):
        resp = graph_client.get("/graph/test/graph?type=imports")
        assert resp.status_code == 200

    def test_response_has_nodes_and_edges(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=imports").json()
        assert "nodes" in data
        assert "edges" in data

    def test_source_files_are_nodes(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=imports").json()
        node_ids = {n["id"] for n in data["nodes"]}
        assert any("math_utils" in nid for nid in node_ids)
        assert any("helpers" in nid for nid in node_ids)

    def test_nodes_have_required_fields(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=imports").json()
        for node in data["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "file" in node

    def test_source_nodes_have_file(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=imports").json()
        for node in data["nodes"]:
            if node["type"] == "source":
                assert node["file"] is not None

    def test_external_nodes_have_null_file(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=imports").json()
        for node in data["nodes"]:
            if node["type"] == "external":
                assert node["file"] is None

    def test_edges_have_required_fields(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=imports").json()
        for edge in data["edges"]:
            assert "from" in edge
            assert "to" in edge
            assert edge["type"] == "imports"

    def test_no_self_loops(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=imports").json()
        for edge in data["edges"]:
            assert edge["from"] != edge["to"]

    def test_no_duplicate_edges(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=imports").json()
        pairs = [(e["from"], e["to"]) for e in data["edges"]]
        assert len(pairs) == len(set(pairs))

    def test_external_imports_present(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=imports").json()
        external_ids = {n["id"] for n in data["nodes"] if n["type"] == "external"}
        assert "os" in external_ids or "pathlib" in external_ids


# ---------------------------------------------------------------------------
# Call graph
# ---------------------------------------------------------------------------

class TestCallGraph:
    def test_returns_200_for_known_root(self, graph_client):
        resp = graph_client.get("/graph/test/graph?type=calls&root=multiply")
        assert resp.status_code == 200

    def test_response_has_nodes_and_edges(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=calls&root=multiply").json()
        assert "nodes" in data
        assert "edges" in data

    def test_root_node_is_present(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=calls&root=multiply").json()
        node_ids = {n["id"] for n in data["nodes"]}
        assert "add" in node_ids

    def test_nodes_have_required_fields(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=calls&root=multiply").json()
        for node in data["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "file" in node

    def test_edges_have_required_fields(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=calls&root=multiply").json()
        for edge in data["edges"]:
            assert "from" in edge
            assert "to" in edge
            assert edge["type"] == "calls"

    def test_no_duplicate_edges(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=calls&root=multiply").json()
        pairs = [(e["from"], e["to"]) for e in data["edges"]]
        assert len(pairs) == len(set(pairs))

    def test_multiply_calls_add(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=calls&root=multiply&depth=1").json()
        callees = {e["to"] for e in data["edges"]}
        assert "add" in callees

    def test_depth_limits_traversal(self, graph_client):
        data_d1 = graph_client.get("/graph/test/graph?type=calls&root=multiply&depth=1").json()
        data_d3 = graph_client.get("/graph/test/graph?type=calls&root=multiply&depth=3").json()
        assert len(data_d3["nodes"]) >= len(data_d1["nodes"])

    def test_method_call_graph(self, graph_client):
        resp = graph_client.get("/graph/test/graph?type=calls&root=Calculator.compute")
        assert resp.status_code == 200
        data = resp.json()
        node_ids = {n["id"] for n in data["nodes"]}
        assert "Calculator.compute" in node_ids

    def test_internal_nodes_have_file(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=calls&root=multiply").json()
        for node in data["nodes"]:
            if node["type"] in ("function", "method"):
                assert node["file"] is not None

    def test_external_nodes_have_null_file(self, graph_client):
        data = graph_client.get("/graph/test/graph?type=calls&root=multiply").json()
        for node in data["nodes"]:
            if node["type"] == "external":
                assert node["file"] is None
