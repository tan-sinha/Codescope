"""
E2E tests for the FastAPI app using TestClient.
clone_repo is patched to avoid network calls — a local temp repo is used instead.
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

def add(x: int, y: int) -> int:
    \"\"\"Return x + y.\"\"\"
    return x + y

def subtract(x: int, y: int) -> int:
    return x - y

class Calculator:
    \"\"\"Simple calculator class.\"\"\"

    def __init__(self):
        self.history = []

    @property
    def last(self):
        return self.history[-1] if self.history else None

    def compute(self, op, a, b):
        result = add(a, b) if op == "add" else subtract(a, b)
        self.history.append(result)
        return result
"""


@pytest.fixture(scope="module")
def fake_repo():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "math_utils.py").write_text(FIXTURE_SRC)
        yield root


@pytest.fixture(scope="module")
def client(fake_repo):
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def indexed_client(fake_repo):
    knowledge_store.clear()
    with TestClient(app) as c:
        with patch("app.routers.index.clone_repo", return_value=fake_repo):
            resp = c.post("/index", json={"owner": "test", "repo": "repo"})
            assert resp.status_code == 200, resp.text
        yield c
    knowledge_store.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /index
# ---------------------------------------------------------------------------

class TestIndexEndpoint:
    def test_index_returns_200(self, fake_repo):
        knowledge_store.clear()
        with TestClient(app) as c:
            with patch("app.routers.index.clone_repo", return_value=fake_repo):
                resp = c.post("/index", json={"owner": "test", "repo": "repo"})
        assert resp.status_code == 200

    def test_index_response_shape(self, fake_repo):
        knowledge_store.clear()
        with TestClient(app) as c:
            with patch("app.routers.index.clone_repo", return_value=fake_repo):
                resp = c.post("/index", json={"owner": "test", "repo": "repo"})
        data = resp.json()
        assert data["owner"] == "test"
        assert data["repo"] == "repo"
        assert data["status"] == "ready"
        assert data["file_count"] >= 1
        assert data["function_count"] >= 2
        assert data["class_count"] >= 1

    def test_index_missing_fields_returns_422(self, client):
        resp = client.post("/index", json={"owner": "test"})
        assert resp.status_code == 422

    def test_index_sets_status_ready(self, fake_repo):
        knowledge_store.clear()
        with TestClient(app) as c:
            with patch("app.routers.index.clone_repo", return_value=fake_repo):
                resp = c.post("/index", json={"owner": "test", "repo": "repo"})
        assert resp.json()["status"] == "ready"


# ---------------------------------------------------------------------------
# GET /explore/{owner}/{repo}
# ---------------------------------------------------------------------------

class TestExploreRepo:
    def test_returns_200_after_index(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo")
        assert resp.status_code == 200

    def test_returns_file_list(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo")
        data = resp.json()
        assert "files" in data
        assert len(data["files"]) >= 1

    def test_returns_function_keys(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo")
        data = resp.json()
        assert "functions" in data
        assert any("add" in k for k in data["functions"])

    def test_returns_class_keys(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo")
        data = resp.json()
        assert "classes" in data
        assert any("Calculator" in k for k in data["classes"])

    def test_not_indexed_returns_404(self, client):
        resp = client.get("/explore/nobody/nothing")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /explore/{owner}/{repo}/function/{name}
# ---------------------------------------------------------------------------

class TestExploreFunction:
    def test_known_function_returns_200(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/function/add")
        assert resp.status_code == 200

    def test_function_response_has_name(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/function/add")
        assert resp.json()["name"] == "add"

    def test_function_has_parameters(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/function/add")
        params = resp.json()["parameters"]
        names = [p["name"] for p in params]
        assert "x" in names
        assert "y" in names

    def test_function_has_return_type(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/function/add")
        assert resp.json()["return_type"] == "int"

    def test_function_has_docstring(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/function/add")
        assert resp.json()["docstring"] is not None

    def test_function_has_summary(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/function/add")
        assert resp.json()["summary"] is not None

    def test_unknown_function_returns_404(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/function/nonexistent")
        assert resp.status_code == 404

    def test_not_indexed_repo_returns_404(self, client):
        resp = client.get("/explore/nobody/nothing/function/foo")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /explore/{owner}/{repo}/class/{name}
# ---------------------------------------------------------------------------

class TestExploreClass:
    def test_known_class_returns_200(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/class/Calculator")
        assert resp.status_code == 200

    def test_class_response_has_name(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/class/Calculator")
        assert resp.json()["name"] == "Calculator"

    def test_class_has_docstring(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/class/Calculator")
        assert resp.json()["docstring"] is not None

    def test_class_has_methods(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/class/Calculator")
        methods = resp.json()["methods"]
        method_names = [m["name"] for m in methods]
        assert "__init__" in method_names
        assert "compute" in method_names

    def test_decorated_method_included(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/class/Calculator")
        methods = resp.json()["methods"]
        method_names = [m["name"] for m in methods]
        assert "last" in method_names

    def test_unknown_class_returns_404(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/class/Nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /explore/{owner}/{repo}/module/{path}
# ---------------------------------------------------------------------------

class TestExploreModule:
    def test_known_module_returns_200(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/module/math_utils.py")
        assert resp.status_code == 200

    def test_module_has_path(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/module/math_utils.py")
        assert resp.json()["path"] == "math_utils.py"

    def test_module_lists_functions(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/module/math_utils.py")
        assert "add" in resp.json()["functions"]
        assert "subtract" in resp.json()["functions"]

    def test_module_lists_classes(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/module/math_utils.py")
        assert "Calculator" in resp.json()["classes"]

    def test_module_has_summary(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/module/math_utils.py")
        assert resp.json()["summary"] is not None

    def test_unknown_module_returns_404(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/module/does_not_exist.py")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /explore/{owner}/{repo}/file/{path}
# ---------------------------------------------------------------------------

class TestExploreFile:
    def test_known_file_returns_200(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/file/math_utils.py")
        assert resp.status_code == 200

    def test_file_response_has_module(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/file/math_utils.py")
        assert "module" in resp.json()

    def test_file_response_has_functions(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/file/math_utils.py")
        fns = resp.json()["functions"]
        names = [f["name"] for f in fns]
        assert "add" in names
        assert "subtract" in names

    def test_file_response_has_classes(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/file/math_utils.py")
        classes = resp.json()["classes"]
        assert any(c["name"] == "Calculator" for c in classes)

    def test_file_response_has_imports(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/file/math_utils.py")
        assert "imports" in resp.json()

    def test_unknown_file_returns_404(self, indexed_client):
        resp = indexed_client.get("/explore/test/repo/file/ghost.py")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /search — search indexes not yet built, expects 404
# ---------------------------------------------------------------------------

class TestSearchEndpoint:
    def test_search_returns_200_after_index(self, indexed_client):
        resp = indexed_client.post(
            "/search",
            json={"owner": "test", "repo": "repo", "query": "add numbers"},
        )
        assert resp.status_code == 200

    def test_search_returns_grouped_results(self, indexed_client):
        resp = indexed_client.post(
            "/search",
            json={"owner": "test", "repo": "repo", "query": "add numbers"},
        )
        data = resp.json()
        assert "results" in data
        assert isinstance(data["results"], list)
        # Each entry is a file group
        for group in data["results"]:
            assert "file" in group
            assert "items" in group
            assert "relevance_score" in group

    def test_search_group_items_have_required_fields(self, indexed_client):
        resp = indexed_client.post(
            "/search",
            json={"owner": "test", "repo": "repo", "query": "calculator compute"},
        )
        for group in resp.json()["results"]:
            for item in group["items"]:
                assert "type" in item
                assert "name" in item
                assert "relevance_score" in item

    def test_search_groups_ordered_by_relevance(self, indexed_client):
        resp = indexed_client.post(
            "/search",
            json={"owner": "test", "repo": "repo", "query": "add numbers"},
        )
        groups = resp.json()["results"]
        scores = [g["relevance_score"] for g in groups]
        assert scores == sorted(scores, reverse=True)

    def test_search_no_duplicate_functions_and_methods(self, indexed_client):
        resp = indexed_client.post(
            "/search",
            json={"owner": "test", "repo": "repo", "query": "calculator compute"},
        )
        for group in resp.json()["results"]:
            fn_names = {i["name"] for i in group["items"] if i["type"] == "function"}
            for item in group["items"]:
                if item["type"] == "method":
                    base = item["name"].split(".")[-1]
                    assert base not in fn_names, f"method {item['name']} duplicates a function"

    def test_search_excludes_test_files(self, indexed_client):
        resp = indexed_client.post(
            "/search",
            json={"owner": "test", "repo": "repo", "query": "add numbers"},
        )
        for group in resp.json()["results"]:
            assert not group["file"].startswith("test_")

    def test_search_class_summary_is_short(self, indexed_client):
        resp = indexed_client.post(
            "/search",
            json={"owner": "test", "repo": "repo", "query": "calculator"},
        )
        for group in resp.json()["results"]:
            for item in group["items"]:
                if item["type"] == "class" and item.get("summary"):
                    assert len(item["summary"]) <= 300

    def test_search_respects_limit(self, indexed_client):
        resp = indexed_client.post(
            "/search",
            json={"owner": "test", "repo": "repo", "query": "add", "limit": 2},
        )
        total_items = sum(len(g["items"]) for g in resp.json()["results"])
        assert total_items <= 2

    def test_search_unindexed_repo_returns_404(self, client):
        resp = client.post(
            "/search",
            json={"owner": "nobody", "repo": "nothing", "query": "test"},
        )
        assert resp.status_code == 404

    def test_search_missing_fields_returns_422(self, client):
        resp = client.post("/search", json={"owner": "test"})
        assert resp.status_code == 422
